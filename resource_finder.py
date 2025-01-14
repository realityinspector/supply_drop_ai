from flask import Blueprint, render_template, request, jsonify, session
from openai import OpenAI

resource_finder_bp = Blueprint('resource_finder', __name__)
client = OpenAI()

@resource_finder_bp.route('/')
def index():
    """Show the resource finder chat interface"""
    return render_template('resources/chat.html')

@resource_finder_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get current conversation context from session
    context = session.get('chat_context', [])
    
    # Add user message to context
    context.append({"role": "user", "content": data['message']})
    
    try:
        # Get AI response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful resource finder for emergency preparedness and disaster response. 
                    Your goal is to help users find relevant resources, information, and assistance for emergency situations.
                    Focus on providing actionable information and reliable resources. Be concise and clear in your responses."""
                },
                *context
            ]
        )
        
        # Get assistant's response
        assistant_message = response.choices[0].message.content
        
        # Add assistant response to context
        context.append({"role": "assistant", "content": assistant_message})
        
        # Keep only last few messages in context to prevent session bloat
        context = context[-4:]  # Keep last 2 exchanges (4 messages)
        
        # Update session
        session['chat_context'] = context
        
        return jsonify({
            'response': assistant_message
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@resource_finder_bp.route('/clear', methods=['POST'])
def clear_chat():
    """Clear chat context from session"""
    if 'chat_context' in session:
        del session['chat_context']
    return jsonify({'success': True}) 