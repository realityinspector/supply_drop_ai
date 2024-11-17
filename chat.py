import os
from openai import OpenAI
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import db
from models import Chat, Message, Document
from document_processor import process_document
import time

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
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
    return render_template('chat.html', chats=chats)

@chat_bp.route('/documents')
@login_required
def documents():
    documents = Document.query.filter_by(user_id=current_user.id).all()
    return render_template('documents.html', documents=documents)

@chat_bp.route('/checklists')
@login_required
def checklists():
    return render_template('checklists.html')

@chat_bp.route('/chat/new', methods=['POST'])
@login_required
def new_chat():
    try:
        chat = Chat(user_id=current_user.id, title="New Chat")
        db.session.add(chat)
        db.session.commit()
        return jsonify({'chat_id': chat.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/chat/<int:chat_id>/messages')
@login_required
def get_chat_messages(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    if chat.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    messages = [{'role': msg.role, 'content': msg.content} for msg in chat.messages]
    return jsonify({'messages': messages})

@chat_bp.route('/chat/<int:chat_id>/message', methods=['POST'])
@login_required
def send_message(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    if chat.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    content = request.json.get('message')
    if not content:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # Save user message
    user_message = Message(chat_id=chat_id, content=content, role='user')
    db.session.add(user_message)
    db.session.commit()

    # Get chat context
    messages = [{"role": msg.role, "content": msg.content} 
                for msg in chat.messages[-5:]]  # Last 5 messages for context

    # Call OpenAI API with exponential backoff
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",  # Using the latest model as per blueprint
                messages=[
                    {"role": "system", "content": "You are SUPPLY DROP AI, an expert in emergency preparedness and disaster response. Provide clear, actionable advice to help users prepare for and respond to emergencies."},
                    *messages
                ],
                temperature=0.7,
                max_tokens=1000
            )
            assistant_content = response.choices[0].message.content
            break
        except Exception as e:
            if attempt == max_attempts - 1:
                return jsonify({'error': f'Failed to get response: {str(e)}'}), 500
            exponential_backoff(attempt)

    # Save assistant message
    assistant_message = Message(chat_id=chat_id, content=assistant_content, role='assistant')
    db.session.add(assistant_message)
    db.session.commit()

    return jsonify({
        'message': assistant_content
    })

@chat_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    processing_type = request.form.get('processing_type', 'text')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check file size
    if len(file.read()) > 16 * 1024 * 1024:  # 16MB limit
        return jsonify({'error': 'File size exceeds 16MB limit'}), 400
    file.seek(0)  # Reset file pointer after reading

    try:
        # Create document with pending status
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            content='',  # Will be updated after processing
            processing_type=processing_type,
            processing_status='pending'
        )
        db.session.add(document)
        db.session.commit()

        # Process the document
        processed_result = process_document(file, processing_type)
        
        # Update document with processed content
        document.content = processed_result.get('raw_text', '')
        document.processed_content = processed_result
        document.processing_status = 'completed'
        db.session.commit()

        return jsonify({
            'message': 'Document uploaded and processed successfully',
            'document_id': document.id
        })
    except ValueError as e:
        if document.id:
            document.processing_status = 'failed'
            db.session.commit()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        if document.id:
            document.processing_status = 'failed'
            db.session.commit()
        db.session.rollback()
        return jsonify({'error': f'Error processing document: {str(e)}'}), 500
