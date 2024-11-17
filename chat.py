import os
import json
import logging
from openai import OpenAI
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import db
from models import Chat, Message, Document, InsuranceRequirement, InsuranceClaim
from document_processor import process_document, analyze_insurance_claim
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)
client = OpenAI()  # This will use OPENAI_API_KEY from env

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
    documents = Document.query.filter_by(user_id=current_user.id).all()
    requirements = InsuranceRequirement.query.filter_by(user_id=current_user.id).all()
    claims = InsuranceClaim.query.filter_by(user_id=current_user.id).all()
    return render_template('documents.html', 
                         documents=documents,
                         requirements=requirements,
                         claims=claims)

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

        # Get chat context
        context_messages = [{"role": msg.role, "content": msg.content} 
                          for msg in chat.messages[-5:]]  # Last 5 messages for context

        # Call OpenAI API with exponential backoff
        max_attempts = 5
        assistant_content = None
        for attempt in range(max_attempts):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",  # Using the latest model as per blueprint
                    messages=[
                        {"role": "system", "content": "You are SUPPLY DROP AI, an expert in emergency preparedness and disaster response. Provide clear, actionable advice to help users prepare for and respond to emergencies."},
                        *context_messages
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                assistant_content = response.choices[0].message.content
                break
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
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    processing_type = request.form.get('processing_type', 'text')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
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
            content='',  # Will be updated after processing
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
        if document.id:
            document.processing_status = 'failed'
            db.session.commit()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        if document.id:
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

        logger.info(f"Starting insurance analysis - Type: {analysis_type}, Claim Doc: {claim_doc_id}, Req Doc: {req_doc_id}")

        if not all([claim_doc_id, req_doc_id, analysis_type]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Verify document ownership and access
        claim_doc = Document.query.get_or_404(claim_doc_id)
        req_doc = Document.query.get_or_404(req_doc_id)
        
        if claim_doc.user_id != current_user.id or req_doc.user_id != current_user.id:
            logger.warning(f"Unauthorized access attempt - User: {current_user.id}, Claim Doc: {claim_doc_id}, Req Doc: {req_doc_id}")
            return jsonify({'error': 'Unauthorized access'}), 403

        # Create a new chat for the analysis
        chat = Chat(user_id=current_user.id, title=f"Insurance Analysis - {analysis_type}")
        db.session.add(chat)

        # Analyze the claim
        logger.info(f"Processing analysis for chat {chat.id}")
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
        logger.info(f"Analysis completed successfully - Chat ID: {chat.id}, Claim ID: {claim.id}")

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
