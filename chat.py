import os
import json
import logging
from openai import OpenAI
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, Response, abort
from flask_login import login_required, current_user
from extensions import db
from models import Chat, Message, Document, InsuranceRequirement, InsuranceClaim
from document_processor import process_document, analyze_insurance_claim
import time
from typing import List, Dict, Any, Optional
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam

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

@chat_bp.route('/insurance')
@login_required
def insurance_wizard():
    current_step = session.get('insurance_step', 1)
    previous_documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    return render_template('insurance/wizard.html', current_step=current_step, previous_documents=previous_documents)

@chat_bp.route('/insurance/upload-requirements', methods=['POST'])
@login_required
def upload_requirements():
    try:
        reuse_doc_id = request.form.get('reuse_document_id')
        if reuse_doc_id:
            document = Document.query.get_or_404(reuse_doc_id)
            if document.user_id != current_user.id:
                flash('Unauthorized access to document', 'error')
                return redirect(url_for('chat.insurance_wizard'))
            
            session['insurance_step'] = 2
            session['requirements_doc_id'] = document.id
            flash('Successfully reused existing document', 'success')
            return redirect(url_for('chat.insurance_wizard'))
        
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
            processing_type='insurance_requirements'
        )
        db.session.add(document)
        db.session.commit()

        processed_result = process_document(file, 'insurance_requirements')
        document.content = processed_result.get('raw_text', '')
        document.processed_content = processed_result
        document.processing_status = 'completed'

        session['insurance_step'] = 2
        session['requirements_doc_id'] = document.id
        
        db.session.commit()
        flash('Requirements document processed successfully', 'success')
        return redirect(url_for('chat.insurance_wizard'))

    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('chat.insurance_wizard'))

@chat_bp.route('/insurance/upload-claim', methods=['POST'])
@login_required
def upload_claim():
    try:
        if not session.get('requirements_doc_id'):
            flash('Please upload requirements document first', 'error')
            return redirect(url_for('chat.insurance_wizard'))

        reuse_doc_id = request.form.get('reuse_document_id')
        if reuse_doc_id:
            document = Document.query.get_or_404(reuse_doc_id)
            if document.user_id != current_user.id:
                flash('Unauthorized access to document', 'error')
                return redirect(url_for('chat.insurance_wizard'))
            
            session['insurance_step'] = 3
            session['claim_doc_id'] = document.id
            flash('Successfully reused existing document', 'success')
            return redirect(url_for('chat.insurance_wizard'))
        
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

        session['insurance_step'] = 3
        session['claim_doc_id'] = document.id
        
        db.session.commit()
        flash('Claim document processed successfully', 'success')
        return redirect(url_for('chat.insurance_wizard'))

    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('chat.insurance_wizard'))

@chat_bp.route('/insurance/analyze', methods=['POST'])
@login_required
def analyze_documents():
    try:
        if not session.get('requirements_doc_id') or not session.get('claim_doc_id'):
            flash('Please upload both requirements and claim documents first', 'error')
            return redirect(url_for('chat.insurance_wizard'))

        analysis_type = request.form.get('analysis_type')
        if not analysis_type:
            flash('Analysis type is required', 'error')
            return redirect(url_for('chat.insurance_wizard'))

        chat = Chat(user_id=current_user.id, title=f"Insurance Analysis - {analysis_type}")
        db.session.add(chat)

        claim_doc = Document.query.get_or_404(session['claim_doc_id'])
        req_doc = Document.query.get_or_404(session['requirements_doc_id'])

        analysis_result = analyze_insurance_claim(
            claim_doc.content,
            req_doc.content,
            analysis_type
        )

        claim = InsuranceClaim(
            user_id=current_user.id,
            requirement_id=session['requirements_doc_id'],
            document_id=session['claim_doc_id'],
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

        session.pop('insurance_step', None)
        session.pop('requirements_doc_id', None)
        session.pop('claim_doc_id', None)

        flash('Analysis completed successfully', 'success')
        return redirect(url_for('chat.chat_view', chat_id=chat.id))

    except Exception as e:
        flash(f'Error during analysis: {str(e)}', 'error')
        return redirect(url_for('chat.insurance_wizard'))

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
    return render_template('chat/detail.html', chat=chat, messages=messages)

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
        system_message = f"You are an AI assistant. Here's the context from the user's documents:\n\n"
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