import os
import json
import logging
from openai import OpenAI
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import db
from models import Chat, Message, Document, InsuranceRequirement, InsuranceClaim
from document_processor import process_document, analyze_insurance_claim
import time
from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
client = OpenAI()

def exponential_backoff(attempt):
    time.sleep(min(2 ** attempt, 60))

@chat_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_page'))
    return render_template('index.html')

@chat_bp.route('/chat')
@login_required
def chat_page():
    chat_id = request.args.get('chat_id')
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
    return render_template('chat.html', chats=chats, active_chat_id=chat_id)

@chat_bp.route('/documents')
@login_required
def documents():
    """Show the insurance document processing overview."""
    return render_template('insurance/start.html')

@chat_bp.route('/insurance/upload')
@login_required
def insurance_upload():
    """Start the insurance document upload process."""
    # Reset the session state
    session['insurance_step'] = 1
    session['can_proceed'] = False
    session['requirements_doc_id'] = None
    session['claim_doc_id'] = None
    return redirect(url_for('chat.insurance_step', step=1))

@chat_bp.route('/insurance/upload-requirements', methods=['POST'])
@login_required
def upload_requirements():
    """Handle insurance requirements document upload."""
    try:
        logger.info("Starting requirements document upload process")
        
        # Validate request has file
        if 'file' not in request.files:
            logger.error("No file found in request.files")
            logger.debug(f"Request files: {request.files}")
            logger.debug(f"Request form: {request.form}")
            flash('No file provided', 'error')
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        logger.info(f"Received file: {file.filename}")
        
        if file.filename == '':
            logger.error("Empty filename received")
            flash('No file selected', 'error')
            return jsonify({'error': 'No file selected'}), 400

        # Validate file size
        file_content = file.read()
        file_size = len(file_content)
        if file_size > 16 * 1024 * 1024:  # 16MB limit
            logger.error(f"File size ({file_size} bytes) exceeds limit")
            flash('File size exceeds 16MB limit', 'error')
            return jsonify({'error': 'File size exceeds 16MB limit'}), 400
        
        file.seek(0)  # Reset file pointer after reading

        # Process the file
        logger.info("Creating document record")
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            content='',
            processing_type='insurance_requirements'
        )
        db.session.add(document)
        db.session.commit()
        logger.info(f"Created document record with ID: {document.id}")

        # Process the document
        logger.info("Processing document content")
        processed_result = process_document(file, 'insurance_requirements')
        
        # Update document with processed content
        document.content = processed_result.get('raw_text', '')
        document.processed_content = processed_result
        document.processing_status = 'completed'

        # Create requirement records
        if isinstance(processed_result, dict):
            requirements = processed_result.get('requirements', [])
            for req in requirements:
                if isinstance(req, dict):
                    requirement = InsuranceRequirement(
                        user_id=current_user.id,
                        document_id=document.id,
                        requirement_text=req.get('requirement_text', ''),
                        category=req.get('category'),
                        priority=req.get('priority')
                    )
                    db.session.add(requirement)

        db.session.commit()
        logger.info("Document processing completed successfully")

        # Update session state
        session['insurance_step'] = 2
        session['can_proceed'] = True
        session['requirements_doc_id'] = document.id

        flash('Requirements document uploaded successfully!', 'success')
        return jsonify({
            'message': 'Requirements document uploaded successfully',
            'document_id': document.id,
            'next_step_url': url_for('chat.insurance_step', step=2)
        })

    except Exception as e:
        logger.error(f"Error uploading requirements: {str(e)}", exc_info=True)
        flash('Error uploading document', 'error')
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/checklists')
@login_required
def checklists():
    return render_template('checklists.html')

@chat_bp.route('/chat/new', methods=['POST'])
@login_required
def new_chat():
    try:
        chat = Chat(user_id=current_user.id)
        db.session.add(chat)
        db.session.commit()
        return jsonify({'chat_id': chat.id})
    except Exception as e:
        logger.error(f"Error creating new chat: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/chat/<int:chat_id>/messages')
@login_required
def get_chat_messages(chat_id):
    try:
        chat = Chat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        messages = [{'role': msg.role, 'content': msg.content} for msg in chat.messages]
        return jsonify({'messages': messages})
    except Exception as e:
        logger.error(f"Error fetching chat messages: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/chat/<int:chat_id>/message', methods=['POST'])
@login_required
def send_message(chat_id):
    try:
        chat = Chat.query.get_or_404(chat_id)
        if chat.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        if not request.is_json:
            return jsonify({'error': 'Invalid request format'}), 400

        data = request.get_json()
        content = data.get('message') if data else None
        if not content:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Save user message
        user_message = Message(chat_id=chat_id, content=content, role='user')
        db.session.add(user_message)
        db.session.commit()

        # Get chat context and properly format messages for OpenAI
        context_messages: List[ChatCompletionMessageParam] = []
        for msg in chat.messages[-5:]:  # Last 5 messages for context
            if msg.role == 'user':
                context_messages.append(ChatCompletionUserMessageParam(role="user", content=msg.content))
            elif msg.role == 'assistant':
                context_messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=msg.content))

        # Create system message
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": "You are SUPPLY DROP AI, an expert in emergency preparedness and disaster response. Provide clear, actionable advice to help users prepare for and respond to emergencies."
        }

        # Call OpenAI API with exponential backoff
        max_attempts = 5
        assistant_content = None
        for attempt in range(max_attempts):
            try:
                messages = [system_message] + context_messages
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                if response.choices and response.choices[0].message and response.choices[0].message.content:
                    assistant_content = response.choices[0].message.content
                    break
                else:
                    raise Exception("Empty response from OpenAI")
                    
            except Exception as e:
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {str(e)}")
                if attempt == max_attempts - 1:
                    return jsonify({'error': f'Failed to get response: {str(e)}'}), 500
                exponential_backoff(attempt)

        if assistant_content:
            # Save assistant message
            assistant_message = Message(chat_id=chat_id, content=assistant_content, role='assistant')
            db.session.add(assistant_message)
            db.session.commit()

            return jsonify({
                'message': assistant_content
            })
        
        return jsonify({'error': 'Failed to generate response'}), 500
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    document: Optional[Document] = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        processing_type = request.form.get('processing_type', 'text')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check for duplicate document
        existing_document = Document.query.filter_by(
            user_id=current_user.id,
            filename=file.filename
        ).first()
        
        if existing_document:
            return jsonify({
                'error': 'A document with this name already exists'
            }), 409

        # Check file size
        if len(file.read()) > 16 * 1024 * 1024:  # 16MB limit
            return jsonify({'error': 'File size exceeds 16MB limit'}), 400
        file.seek(0)  # Reset file pointer after reading

        # Create document with pending status
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            content='',
            processing_type=processing_type
        )
        db.session.add(document)
        db.session.commit()

        # Process the document
        processed_result = process_document(file, processing_type)
        
        # Update document with processed content
        document.content = processed_result.get('raw_text', '')
        document.processed_content = processed_result
        document.processing_status = 'completed'

        # If this is an insurance requirements document, create requirement records
        if processing_type == 'insurance_requirements' and isinstance(processed_result, dict):
            requirements = processed_result.get('requirements', [])
            for req in requirements:
                if isinstance(req, dict):
                    requirement = InsuranceRequirement(
                        user_id=current_user.id,
                        document_id=document.id,
                        requirement_text=req.get('requirement_text', ''),
                        category=req.get('category'),
                        priority=req.get('priority')
                    )
                    db.session.add(requirement)

        db.session.commit()
        logger.info(f"Document uploaded successfully: {file.filename}")

        return jsonify({
            'message': 'Document uploaded and processed successfully',
            'document_id': document.id
        })

    except ValueError as e:
        logger.error(f"Value error processing document: {str(e)}")
        if document:
            document.processing_status = 'failed'
            db.session.commit()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        if document:
            document.processing_status = 'failed'
            db.session.commit()
        db.session.rollback()
        return jsonify({'error': f'Error processing document: {str(e)}'}), 500

@chat_bp.route('/insurance-analysis', methods=['POST'])
@login_required
def analyze_insurance():
    try:
        if not request.is_json:
            return jsonify({'error': 'Invalid request format'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        claim_doc_id = data.get('claim_document_id')
        req_doc_id = data.get('requirement_document_id')
        analysis_type = data.get('analysis_type')

        if not all([claim_doc_id, req_doc_id, analysis_type]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Verify document ownership and access
        claim_doc = Document.query.get_or_404(claim_doc_id)
        req_doc = Document.query.get_or_404(req_doc_id)
        
        if claim_doc.user_id != current_user.id or req_doc.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized access'}), 403

        # Create a new chat for the analysis
        chat = Chat(user_id=current_user.id, title=f"Insurance Analysis - {analysis_type}")
        db.session.add(chat)

        # Analyze the claim
        analysis_result = analyze_insurance_claim(
            claim_doc.content,
            req_doc.content,
            analysis_type
        )

        # Create a claim record
        claim = InsuranceClaim(
            user_id=current_user.id,
            requirement_id=req_doc_id,
            document_id=claim_doc_id,
            analysis_type=analysis_type,
            analysis_result=analysis_result
        )
        db.session.add(claim)

        # Add the analysis result as a message in the chat
        message = Message(
            chat_id=chat.id,
            content=json.dumps(analysis_result, indent=2),
            role='assistant'
        )
        db.session.add(message)
        
        db.session.commit()

        return jsonify({
            'message': 'Analysis completed successfully',
            'chat_id': chat.id,
            'claim_id': claim.id,
            'analysis_result': analysis_result
        })

    except Exception as e:
        logger.error(f"Error in insurance analysis: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': str(e),
            'details': 'An error occurred during analysis. Please try again.'
        }), 500

@chat_bp.route('/workflow-state')
@login_required
def get_workflow_state():
    """Get the current state of the insurance document workflow."""
    try:
        # Find the most recent insurance requirements document
        requirements_doc = Document.query.filter_by(
            user_id=current_user.id,
            processing_type='insurance_requirements',
            processing_status='completed'
        ).order_by(Document.uploaded_at.desc()).first()

        # Find the most recent insurance claim document
        claim_doc = Document.query.filter_by(
            user_id=current_user.id,
            processing_type='insurance_claim',
            processing_status='completed'
        ).order_by(Document.uploaded_at.desc()).first()

        return jsonify({
            'requirements_doc_id': requirements_doc.id if requirements_doc else None,
            'claim_doc_id': claim_doc.id if claim_doc else None
        })
    except Exception as e:
        logger.error(f"Error getting workflow state: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/insurance/step/<int:step>')
@login_required
def insurance_step(step):
    """Handle insurance workflow steps."""
    if step < 1 or step > 3:
        flash('Invalid step', 'error')
        return redirect(url_for('chat.insurance_step', step=1))

    # Initialize session if needed
    if 'insurance_step' not in session:
        session['insurance_step'] = 1
        session['can_proceed'] = False
        session['requirements_doc_id'] = None
        session['claim_doc_id'] = None

    # Prevent accessing later steps if previous steps are not completed
    if step > session['insurance_step']:
        flash('Please complete the previous step first', 'error')
        return redirect(url_for('chat.insurance_step', step=session['insurance_step']))

    templates = {
        1: 'insurance/step1_requirements.html',
        2: 'insurance/step2_claim.html',
        3: 'insurance/step3_analysis.html'
    }

    return render_template(templates[step])

@chat_bp.route('/insurance/upload-claim', methods=['POST'])
@login_required
def upload_claim():
    """Handle insurance claim document upload."""
    try:
        # Verify previous step is completed
        if not session.get('requirements_doc_id'):
            flash('Please upload requirements document first', 'error')
            return jsonify({'error': 'Requirements document not found'}), 400

        if 'file' not in request.files:
            flash('No file provided', 'error')
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return jsonify({'error': 'No file selected'}), 400

        # Process the file
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            content='',
            processing_type='insurance_claim'
        )
        db.session.add(document)
        db.session.commit()

        # Process the document
        processed_result = process_document(file, 'text')
        
        # Update document with processed content
        document.content = processed_result.get('raw_text', '')
        document.processed_content = processed_result
        document.processing_status = 'completed'
        
        db.session.commit()

        # Update session state
        session['insurance_step'] = 3
        session['can_proceed'] = True
        session['claim_doc_id'] = document.id

        flash('Claim document uploaded successfully!', 'success')
        return jsonify({
            'message': 'Claim document uploaded successfully',
            'document_id': document.id,
            'next_step_url': url_for('chat.insurance_step', step=3)
        })

    except Exception as e:
        logger.error(f"Error uploading claim: {str(e)}")
        flash('Error uploading document', 'error')
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/insurance/analyze', methods=['POST'])
@login_required
def analyze_documents():
    """Handle insurance document analysis."""
    try:
        # Verify required documents are available
        if not session.get('requirements_doc_id') or not session.get('claim_doc_id'):
            flash('Please upload both requirements and claim documents first', 'error')
            return redirect(url_for('chat.insurance_step', step=1))

        analysis_type = request.form.get('analysis_type')
        if not analysis_type:
            flash('Analysis type is required', 'error')
            return redirect(url_for('chat.insurance_step', step=3))

        # Create a new chat for the analysis
        chat = Chat(user_id=current_user.id, title=f"Insurance Analysis - {analysis_type}")
        db.session.add(chat)

        # Get the documents
        claim_doc = Document.query.get_or_404(session['claim_doc_id'])
        req_doc = Document.query.get_or_404(session['requirements_doc_id'])

        # Verify document ownership
        if claim_doc.user_id != current_user.id or req_doc.user_id != current_user.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('chat.insurance_step', step=1))

        # Analyze the documents
        analysis_result = analyze_insurance_claim(
            claim_doc.content,
            req_doc.content,
            analysis_type
        )

        # Create a claim record
        claim = InsuranceClaim(
            user_id=current_user.id,
            requirement_id=session['requirements_doc_id'],
            document_id=session['claim_doc_id'],
            analysis_type=analysis_type,
            analysis_result=analysis_result
        )
        db.session.add(claim)

        # Add the analysis result as a message in the chat
        message = Message(
            chat_id=chat.id,
            content=json.dumps(analysis_result, indent=2),
            role='assistant'
        )
        db.session.add(message)
        
        db.session.commit()

        # Clear the session state after successful analysis
        session.pop('insurance_step', None)
        session.pop('can_proceed', None)
        session.pop('requirements_doc_id', None)
        session.pop('claim_doc_id', None)

        flash('Analysis completed successfully', 'success')
        return redirect(url_for('chat.chat_page', chat_id=chat.id))

    except Exception as e:
        logger.error(f"Error in insurance analysis: {str(e)}")
        flash(f'Error during analysis: {str(e)}', 'error')
        return redirect(url_for('chat.insurance_step', step=3))