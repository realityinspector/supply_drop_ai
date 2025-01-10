import os
import json
import logging
from openai import OpenAI
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, Response, abort, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Chat, Message, Document, InsuranceRequirement, InsuranceClaim
from document_processor import process_document, analyze_insurance_claim
import time
from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
from werkzeug.utils import secure_filename

# Setup logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)
client = OpenAI()

# Custom Jinja filters
@chat_bp.app_template_filter('from_json')
def from_json(value):
    try:
        return json.loads(value)
    except:
        return value

@chat_bp.app_template_filter('pretty_json')
def pretty_json(value):
    try:
        if isinstance(value, str):
            return json.dumps(json.loads(value), indent=2)
        return json.dumps(value, indent=2)
    except:
        return value

def exponential_backoff(attempt):
    time.sleep(min(2 ** attempt, 60))

@chat_bp.route('/')
def index():
    if current_user.is_authenticated:
        user_chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
        user_documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
        
        if not user_chats and not user_documents:
            # First-time user
            return render_template('chat/first_time_user.html')
        else:
            # Returning user
            return render_template('chat/dashboard.html', chats=user_chats, documents=user_documents)
    else:
        # Non-authenticated user
        return render_template('index.html')

@chat_bp.route('/documents')
@login_required
def documents():
    """Show the document processing overview."""
    user_documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    return render_template('documents/list.html', documents=user_documents)

@chat_bp.route('/insurance/wizard')
@login_required
def insurance_wizard():
    step = request.args.get('step', 1, type=int)
    if step not in [1, 2, 3]:
        step = 1
    
    # Get user's workflow state from session
    workflow_state = session.get('workflow_state', {})
    
    # If returning to step 3 and no workflow state, try to get the most recent claim
    if step == 3 and not workflow_state:
        recent_claim = InsuranceClaim.query.filter_by(user_id=current_user.id).order_by(InsuranceClaim.id.desc()).first()
        if recent_claim:
            workflow_state = {
                'requirements_doc_id': recent_claim.requirement_id,
                'claim_doc_id': recent_claim.document_id
            }
            session['workflow_state'] = workflow_state
    
    if step > 1 and not workflow_state.get('requirements_doc_id'):
        flash('Please complete document uploads first', 'error')
        return redirect(url_for('chat.insurance_wizard', step=1))
    
    if step > 2 and not workflow_state.get('claim_doc_id'):
        flash('Please upload claim document first', 'error')
        return redirect(url_for('chat.insurance_wizard', step=2))
    
    previous_documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    
    template_map = {
        1: 'insurance/step1_requirements.html',
        2: 'insurance/step2_claim.html',
        3: 'insurance/step3_analysis.html'
    }
    
    # Get the current document ID based on the step
    current_doc_id = None
    if step == 1:
        current_doc_id = workflow_state.get('requirements_doc_id')
    elif step == 2:
        current_doc_id = workflow_state.get('claim_doc_id')
    
    # If it's an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'requirements_doc_id': workflow_state.get('requirements_doc_id'),
            'claim_doc_id': workflow_state.get('claim_doc_id'),
            'current_step': step
        })
    
    return render_template(
        template_map[step],
        current_step=step,
        previous_documents=previous_documents,
        current_doc_id=current_doc_id
    )

@chat_bp.route('/insurance/reuse-document', methods=['POST'])
@login_required
def reuse_document():
    data = request.get_json()
    document_id = data.get('document_id')
    
    if not document_id:
        return jsonify({'error': 'No document ID provided'}), 400
    
    document = Document.query.filter_by(id=document_id, user_id=current_user.id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    # Update workflow state in session
    workflow_state = session.get('workflow_state', {})
    workflow_state['requirements_doc_id'] = document_id
    session['workflow_state'] = workflow_state
    
    return jsonify({'success': True, 'document_id': document_id})

@chat_bp.route('/insurance/upload-requirements', methods=['POST'])
@login_required
def upload_requirements():
    try:
        reuse_doc_id = request.form.get('reuse_document_id')
        if reuse_doc_id:
            document = Document.query.get_or_404(reuse_doc_id)
            if document.user_id != current_user.id:
                return jsonify({'error': 'Unauthorized access to document'}), 403
            
            # Update workflow state in session
            workflow_state = session.get('workflow_state', {})
            workflow_state['requirements_doc_id'] = document.id
            session['workflow_state'] = workflow_state
            
            return jsonify({
                'success': True,
                'document_id': document.id,
                'filename': document.filename
            })
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Save file and create document record
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        document = Document(
            filename=filename,
            file_path=file_path,
            user_id=current_user.id,
            type='requirements'
        )
        db.session.add(document)
        db.session.commit()
        
        # Update workflow state in session
        workflow_state = session.get('workflow_state', {})
        workflow_state['requirements_doc_id'] = document.id
        session['workflow_state'] = workflow_state
        
        return jsonify({
            'success': True,
            'document_id': document.id,
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f"Error uploading file: {str(e)}")
        return jsonify({'error': 'Failed to upload file'}), 500

def allowed_file(filename):
    """Check if a filename has an allowed extension"""
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md', 'json'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@chat_bp.route('/insurance/upload-claim', methods=['POST'])
@login_required
def upload_claim():
    try:
        workflow_state = session.get('workflow_state', {})
        if not workflow_state.get('requirements_doc_id'):
            flash('Please upload requirements document first', 'error')
            return redirect(url_for('chat.insurance_wizard'))

        reuse_doc_id = request.form.get('reuse_document_id')
        if reuse_doc_id:
            document = Document.query.get_or_404(reuse_doc_id)
            if document.user_id != current_user.id:
                flash('Unauthorized access to document', 'error')
                return redirect(url_for('chat.insurance_wizard'))
            
            workflow_state['claim_doc_id'] = document.id
            session['workflow_state'] = workflow_state
            flash('Successfully reused existing document', 'success')
            return redirect(url_for('chat.insurance_wizard', step=3))
        
        if 'file' not in request.files:
            flash('No file provided', 'error')
            return redirect(url_for('chat.insurance_wizard'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('chat.insurance_wizard'))

        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            content='',
            processing_type='insurance_claim'
        )
        db.session.add(document)
        db.session.commit()

        processed_result = process_document(file, 'text')
        document.content = processed_result.get('raw_text', '')
        document.processed_content = processed_result
        document.processing_status = 'completed'

        workflow_state['claim_doc_id'] = document.id
        session['workflow_state'] = workflow_state
        
        db.session.commit()
        flash('Claim document processed successfully', 'success')
        return redirect(url_for('chat.insurance_wizard', step=3))

    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('chat.insurance_wizard'))

@chat_bp.route('/insurance/analyze', methods=['POST'])
@login_required
def analyze_documents():
    try:
        workflow_state = session.get('workflow_state', {})
        if not workflow_state.get('requirements_doc_id') or not workflow_state.get('claim_doc_id'):
            return jsonify({'error': 'Please upload both requirements and claim documents first'}), 400

        analysis_type = request.form.get('analysis_type')
        if not analysis_type:
            return jsonify({'error': 'Analysis type is required'}), 400

        # Get previous chat ID if this is a follow-up analysis
        previous_chat_id = request.form.get('previous_chat_id')
        previous_messages = []
        if previous_chat_id:
            previous_messages = Message.query.filter_by(chat_id=previous_chat_id).order_by(Message.created_at).all()
            previous_messages = [{"role": msg.role, "content": msg.content} for msg in previous_messages]

        chat = Chat(user_id=current_user.id, title=f"Insurance Analysis - {analysis_type}")
        db.session.add(chat)

        claim_doc = Document.query.get_or_404(workflow_state['claim_doc_id'])
        req_doc = Document.query.get_or_404(workflow_state['requirements_doc_id'])

        try:
            analysis_result = analyze_insurance_claim(
                claim_doc.content,
                req_doc.content,
                analysis_type,
                previous_messages if previous_messages else None
            )
        except ValueError as ve:
            return jsonify({'error': f'Analysis failed: {str(ve)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Unexpected error during analysis: {str(e)}'}), 500

        claim = InsuranceClaim(
            user_id=current_user.id,
            requirement_id=workflow_state['requirements_doc_id'],
            document_id=workflow_state['claim_doc_id'],
            analysis_type=analysis_type,
            analysis_result=analysis_result
        )
        db.session.add(claim)

        message = Message(
            chat_id=chat.id,
            content=json.dumps(analysis_result, indent=2),
            role='assistant'
        )
        db.session.add(message)
        
        db.session.commit()

        # Clear workflow state after analysis
        session.pop('workflow_state', None)

        return jsonify({
            'success': True,
            'chat_id': chat.id,
            'message': 'Analysis completed successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error during analysis: {str(e)}")
        return jsonify({'error': f'Error during analysis: {str(e)}'}), 500

@chat_bp.route('/chat')
@login_required
def chat_page():
    """Display chat list or redirect to specific chat."""
    chat_id = request.args.get('chat_id')
    if chat_id:
        return redirect(url_for('chat.chat_view', chat_id=chat_id))
    
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
    return render_template('chat/list.html', chats=chats)

@chat_bp.route('/chat/<int:chat_id>')
@login_required
def chat_view(chat_id):
    """Display a specific chat conversation."""
    chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
    documents = chat.documents if chat.documents else []

    # Get the insurance claim associated with this chat
    insurance_claim = InsuranceClaim.query.filter_by(user_id=current_user.id).order_by(InsuranceClaim.id.desc()).first()

    return render_template('chat/detail.html', 
                           chat=chat, 
                           messages=messages, 
                           documents=documents,
                           insurance_claim=insurance_claim)

@chat_bp.route('/chat/<int:chat_id>/messages', methods=['POST'])
@login_required
def send_message(chat_id):
    """Handle sending a new message in a chat."""
    try:
        chat = Chat.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
        
        if not request.is_json:
            return jsonify({'error': 'Invalid request format'}), 400

        data = request.get_json()
        content = data.get('content')
        if not content:
            return jsonify({'error': 'Message content is required'}), 400

        # Get conversation history
        messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
        conversation_history = [{"role": msg.role, "content": msg.content} for msg in messages]

        # Get document context
        documents = Document.query.filter_by(user_id=current_user.id).all()
        document_context = [{"filename": doc.filename, "content": doc.content} for doc in documents]

        # Check character limit
        total_chars = sum(len(msg["content"]) for msg in conversation_history) + len(content)
        if total_chars > 250000:
            new_chat_url = url_for('chat.new_chat')
            error_message = f"The conversation has exceeded 250,000 characters. Please start a new conversation. <a href='{new_chat_url}'>Click here to start a new chat</a>"
            return jsonify({'error': error_message, 'warning': True}), 413

        # Prepare system message with document context
        system_message = """You are an AI assistant specialized in analyzing insurance documents and claims. Your role is to:
1. Help users understand their insurance documents
2. Compare claims against policy requirements
3. Identify potential issues or gaps in coverage
4. Provide actionable recommendations
5. Explain complex insurance terms in simple language

Here's the context from the user's documents:
"""
        for doc in document_context:
            system_message += f"Document: {doc['filename']}\nContent: {doc['content'][:500]}...\n\n"

        # Prepare messages for API call
        messages_for_api = [
            {"role": "system", "content": system_message},
            *conversation_history,
            {"role": "user", "content": content}
        ]

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_for_api
        )

        # Save user message
        user_message = Message(chat_id=chat_id, content=content, role='user')
        db.session.add(user_message)

        # Save assistant's response
        assistant_content = response.choices[0].message.content
        assistant_message = Message(chat_id=chat_id, content=assistant_content, role='assistant')
        db.session.add(assistant_message)

        db.session.commit()

        return jsonify({
            'user_message': {'content': content, 'timestamp': user_message.created_at.isoformat()},
            'assistant_message': {'content': assistant_content, 'timestamp': assistant_message.created_at.isoformat()}
        })

    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your message'}), 500

@chat_bp.route('/new_chat', methods=['POST'])
@login_required
def new_chat():
    try:
        # Get the current chat's documents
        current_chat_id = request.form.get('current_chat_id')
        if current_chat_id:
            current_chat = Chat.query.get_or_404(current_chat_id)
            if current_chat.user_id != current_user.id:
                abort(403)
            documents = current_chat.documents
        else:
            documents = []

        # Create a new chat
        new_chat = Chat(user_id=current_user.id, title="New Chat")
        
        # Associate the same documents with the new chat
        new_chat.documents = documents

        db.session.add(new_chat)
        db.session.commit()

        # Redirect to the new chat
        return redirect(url_for('chat.chat_view', chat_id=new_chat.id))
    except Exception as e:
        logger.error(f"Error creating new chat: {str(e)}")
        flash('An error occurred while creating a new chat. Please try again.', 'error')
        return redirect(url_for('chat.chat_page'))

@chat_bp.route('/upload_document', methods=['POST'])
@login_required
def upload_document():
    """Handle a general document upload."""
    try:
        # For example, get the file from the form, do some processing
        file = request.files.get('file')
        processing_type = request.form.get('processing_type', 'text')

        if not file or file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('chat.documents'))

        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            content='',
            processing_type=processing_type
        )
        db.session.add(document)
        db.session.commit()

        processed_result = process_document(file, processing_type)
        document.content = processed_result.get('raw_text', '')
        document.processed_content = processed_result
        document.processing_status = 'completed'
        db.session.commit()

        flash('Document uploaded and processed successfully!', 'success')
        return redirect(url_for('chat.documents'))
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('chat.documents'))

@chat_bp.route('/document/<int:document_id>')
@login_required
def view_document(document_id):
    document = Document.query.get_or_404(document_id)
    if document.user_id != current_user.id:
        abort(403)  # Forbidden if the document doesn't belong to the current user
    return render_template('documents/view.html', document=document)

@chat_bp.route('/insurance/documents')
@login_required
def get_insurance_documents():
    """Return a list of insurance documents for the current user."""
    requirements_documents = Document.query.filter_by(
        user_id=current_user.id,
        processing_type='insurance_requirements'
    ).order_by(Document.uploaded_at.desc()).all()
    
    return jsonify({
        'requirements_documents': [{
            'id': doc.id,
            'filename': doc.filename,
            'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None
        } for doc in requirements_documents]
    })

@chat_bp.route('/insurance/claim-documents')
@login_required
def get_insurance_claim_documents():
    """Return a list of insurance claim documents for the current user."""
    claim_documents = Document.query.filter_by(
        user_id=current_user.id,
        processing_type='insurance_claim'
    ).order_by(Document.uploaded_at.desc()).all()
    
    return jsonify({
        'claim_documents': [{
            'id': doc.id,
            'filename': doc.filename,
            'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None
        } for doc in claim_documents]
    })