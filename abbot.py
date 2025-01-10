from flask import Blueprint, jsonify, request, current_app, render_template
from flask_login import login_required, current_user
from models import db, AbbotConversation, AbbotMessage
import json
from datetime import datetime
import logging
from functools import wraps
from werkzeug.exceptions import HTTPException
from extensions import csrf
from openai import OpenAI
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

bp = Blueprint('abbot', __name__, url_prefix='/abbot')

def handle_error(error):
    """Convert any error to JSON response"""
    logger.error(f"Error occurred: {str(error)}")
    code = 500
    if isinstance(error, HTTPException):
        code = error.code
    return jsonify(error=str(error)), code

# Register error handlers for the blueprint
bp.register_error_handler(Exception, handle_error)
bp.register_error_handler(404, handle_error)
bp.register_error_handler(500, handle_error)

# Exempt API routes from CSRF protection
csrf.exempt(bp)

def json_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return handle_error(e)
    return decorated_function

def get_ai_response(messages):
    """Get AI response using the OpenAI API"""
    try:
        if not client.api_key:
            logger.error("OpenAI API key not configured")
            return "I apologize, but I'm not properly configured yet. Please contact the administrator."

        # Get the system prompt first
        system_prompt = get_system_prompt()
        
        # Prepare the messages for the API
        formatted_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add the conversation history
        formatted_messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role in ['user', 'assistant']  # Only include user and assistant messages
        ])
        
        logger.info(f"Sending request to OpenAI with {len(formatted_messages)} messages")
        
        # Get response from OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=formatted_messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        ai_response = response.choices[0].message.content
        logger.info(f"Received response from OpenAI: {ai_response[:100]}...")
        return ai_response
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"OpenAI API error ({error_type}): {error_msg}")
        
        if "authentication" in error_msg.lower():
            return "I apologize, but I'm having authentication issues. Please contact the administrator."
        elif "rate limit" in error_msg.lower():
            return "I'm currently experiencing high demand. Please try again in a moment."
        else:
            return "I apologize, but I encountered an error processing your request. Please try again."

class ContextManager:
    MAX_CONTEXT_SIZE = 250000
    
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        
    def add_message(self, content, role):
        message = AbbotMessage(
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            token_count=len(content)  # Simple approximation, could use proper tokenizer
        )
        db.session.add(message)
        self._prune_if_needed()
        return message
    
    def get_context(self):
        messages = AbbotMessage.query.filter_by(
            conversation_id=self.conversation_id
        ).order_by(AbbotMessage.created_at.asc()).all()
        return messages
    
    def _prune_if_needed(self):
        messages = self.get_context()
        total_size = sum(len(m.content) for m in messages)
        
        while total_size > self.MAX_CONTEXT_SIZE and messages:
            # Remove oldest message
            oldest = messages.pop(0)
            total_size -= len(oldest.content)
            db.session.delete(oldest)

def get_system_prompt():
    with open('prompt_abbot.json', 'r') as f:
        prompt_data = json.load(f)
    return prompt_data.get('system_prompt_abbot_ai', '')

@bp.route('/')
@bp.route('/chat')
@login_required
def chat():
    logger.info(f"User {current_user.id} accessing chat page")
    return render_template('abbot/chat.html')

@bp.route('/api/conversations', methods=['GET'])
@json_login_required
def list_conversations():
    try:
        logger.info(f"Fetching conversations for user {current_user.id}")
        conversations = AbbotConversation.query.filter_by(
            user_id=current_user.id,
            is_archived=False
        ).order_by(AbbotConversation.updated_at.desc()).all()
        
        result = [{
            'id': c.id,
            'title': c.title,
            'created_at': c.created_at.isoformat(),
            'updated_at': c.updated_at.isoformat()
        } for c in conversations]
        
        logger.info(f"Found {len(conversations)} conversations")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/conversations', methods=['POST'])
@json_login_required
def create_conversation():
    try:
        logger.info(f"Creating new conversation for user {current_user.id}")
        title = request.json.get('title', 'New Conversation')
        
        conversation = AbbotConversation(
            user_id=current_user.id,
            title=title
        )
        db.session.add(conversation)
        db.session.commit()
        
        # Add a friendly welcome message instead of the raw system prompt
        logger.info(f"Adding welcome message to conversation {conversation.id}")
        context_manager = ContextManager(conversation.id)
        welcome_message = (
            "Hello! I'm your Wildfire Relief Companion, here to help with disaster preparedness "
            "and response. I have access to the latest information from the Topanga Mutual Aid "
            "Tracker and can assist with support requests, accommodations, resources, and more. "
            "How can I help you today?"
        )
        context_manager.add_message(welcome_message, 'assistant')
        db.session.commit()
        
        logger.info(f"Successfully created conversation {conversation.id}")
        return jsonify({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/conversations/<int:conv_id>/messages', methods=['GET'])
@json_login_required
def get_messages(conv_id):
    try:
        logger.info(f"Fetching messages for conversation {conv_id}")
        conversation = AbbotConversation.query.get_or_404(conv_id)
        if conversation.user_id != current_user.id:
            logger.warning(f"Unauthorized access attempt to conversation {conv_id} by user {current_user.id}")
            return jsonify({'error': 'Unauthorized'}), 403
            
        messages = AbbotMessage.query.filter_by(
            conversation_id=conv_id
        ).order_by(AbbotMessage.created_at.asc()).all()
        
        logger.info(f"Found {len(messages)} messages")
        return jsonify([m.to_dict() for m in messages])
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/conversations/<int:conv_id>/messages', methods=['POST'])
@json_login_required
def send_message(conv_id):
    try:
        logger.info(f"Sending message to conversation {conv_id}")
        conversation = AbbotConversation.query.get_or_404(conv_id)
        if conversation.user_id != current_user.id:
            logger.warning(f"Unauthorized access attempt to conversation {conv_id} by user {current_user.id}")
            return jsonify({'error': 'Unauthorized'}), 403
        
        content = request.json.get('content')
        if not content:
            logger.warning("Empty message content")
            return jsonify({'error': 'Message content is required'}), 400
        
        context_manager = ContextManager(conv_id)
        
        # Add user message
        user_message = context_manager.add_message(content, 'user')
        
        # Get conversation context and generate AI response
        messages = context_manager.get_context()
        ai_response = get_ai_response(messages)
        ai_message = context_manager.add_message(ai_response, 'assistant')
        
        # Update conversation timestamp and title if it's the first user message
        conversation.updated_at = datetime.utcnow()
        if len(messages) <= 2:  # Only welcome message and this user message
            # Use the first few words of user's message as the title
            title_preview = ' '.join(content.split()[:5])
            conversation.title = f"{title_preview}..."
        db.session.commit()
        
        logger.info(f"Successfully sent message to conversation {conv_id}")
        return jsonify({
            'user_message': user_message.to_dict(),
            'ai_message': ai_message.to_dict()
        })
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': str(e)}), 500 