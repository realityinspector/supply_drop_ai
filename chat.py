import os
import json
import logging
from openai import OpenAI
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, Response
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

        message = Message(
            chat_id=chat_id,
            content=content,
            role='user'
        )
        db.session.add(message)
        db.session.commit()

        try:
            messages = [
                {"role": "system", "content": "You are SUPPLY DROP AI, an expert in emergency preparedness and disaster response."},
                {"role": "user", "content": content}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_content = response.choices[0].message.content if response.choices else "I apologize, but I couldn't generate a response."
            
            ai_message = Message(
                chat_id=chat_id,
                content=ai_content,
                role='assistant'
            )
            db.session.add(ai_message)
            db.session.commit()

            return jsonify({
                'content': ai_content,
                'created_at': ai_message.created_at.isoformat()
            })

        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': str(e)}), 500