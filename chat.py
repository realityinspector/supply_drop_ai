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
@login_required
def index():
    return redirect(url_for('chat.chat_page'))

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
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            assistant_content = response.choices[0].message.content
            break
        except openai.RateLimitError:
            if attempt == max_attempts - 1:
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            exponential_backoff(attempt)
        except openai.APIConnectionError:
            return jsonify({'error': 'Failed to connect to OpenAI API. Please try again later.'}), 503
        except openai.APIError as e:
            return jsonify({'error': f'OpenAI API error: {str(e)}'}), 500
        except Exception as e:
            return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

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
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check file size
    if len(file.read()) > 16 * 1024 * 1024:  # 16MB limit
        return jsonify({'error': 'File size exceeds 16MB limit'}), 400
    file.seek(0)  # Reset file pointer after reading

    try:
        content = process_document(file)
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            content=content
        )
        db.session.add(document)
        db.session.commit()
        return jsonify({'message': 'Document uploaded successfully'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error processing document: {str(e)}'}), 500