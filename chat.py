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
from sqlalchemy.exc import SQLAlchemyError
from abbot import ContextManager, get_system_prompt
import traceback
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

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

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    if not PDF_SUPPORT:
        return f"PDF text extraction not available. File stored at: {file_path}"
    
    try:
        text = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text.append(page.extract_text())
        return '\n'.join(text)
    except Exception as e:
        current_app.logger.error(f"Error extracting text from PDF: {str(e)}")
        return f"Error extracting PDF text. File stored at: {file_path}"

@chat_bp.route('/')
def index():
    """Main chat page - redirects to Abbot AI chat."""
    if not current_user.is_authenticated:
        return render_template('index.html')
    
    return redirect(url_for('abbot.chat'))

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
        current_app.logger.info("Entering upload_requirements function")
        current_app.logger.info(f"UPLOAD_FOLDER configuration: {current_app.config.get('UPLOAD_FOLDER')}")
        
        # Log request information
        current_app.logger.info(f"Request method: {request.method}")
        current_app.logger.info(f"Content type: {request.content_type}")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        
        # Log CSRF token information for debugging
        csrf_token = request.form.get('csrf_token')
        csrf_header = request.headers.get('X-CSRFToken')
        current_app.logger.info(f"CSRF token in form: {bool(csrf_token)}")
        current_app.logger.info(f"CSRF token in header: {bool(csrf_header)}")
        
        reuse_doc_id = request.form.get('reuse_document_id')
        if reuse_doc_id:
            current_app.logger.info(f"Attempting to reuse document with ID: {reuse_doc_id}")
            document = Document.query.get(reuse_doc_id)
            if not document or document.user_id != current_user.id:
                current_app.logger.warning(f"Unauthorized access to document {reuse_doc_id} by user {current_user.id}")
                return jsonify({'error': 'Unauthorized access to document'}), 403
            
            # Update workflow state in session
            workflow_state = session.get('workflow_state', {})
            workflow_state['requirements_doc_id'] = document.id
            session['workflow_state'] = workflow_state
            
            current_app.logger.info(f"Successfully reused document: {document.filename}")
            return jsonify({
                'success': True,
                'document_id': document.id,
                'filename': document.filename
            })
        
        current_app.logger.info("Checking for file in request")
        current_app.logger.info(f"Request files: {list(request.files.keys())}")
        current_app.logger.info(f"Request form: {list(request.form.keys())}")
        
        if 'file' not in request.files:
            current_app.logger.warning("No file provided in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not file.filename:
            current_app.logger.warning("No file selected")
            return jsonify({'error': 'No file selected'}), 400
        
        current_app.logger.info(f"File received: {file.filename}")
        
        # Validate file
        if not allowed_file(file.filename):
            current_app.logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Ensure upload directory exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            current_app.logger.info(f"Creating upload directory: {upload_folder}")
            os.makedirs(upload_folder)
        
        # Save file and create document record
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        current_app.logger.info(f"Saving file to: {file_path}")
        
        try:
            file.save(file_path)
            current_app.logger.info("File saved successfully")
        except Exception as e:
            current_app.logger.error(f"Error saving file: {str(e)}")
            return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
        
        try:
            # Process the file based on its type
            if filename.lower().endswith('.pdf'):
                content = extract_text_from_pdf(file_path)
            else:
                # For text files, read the content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # If UTF-8 fails, try reading as binary
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
            
            document = Document(
                user_id=current_user.id,
                filename=filename,
                file_path=file_path,
                content=content,
                processing_type='requirements'
            )
            db.session.add(document)
            db.session.commit()
            current_app.logger.info("Document record created in database")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error: {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        
        # Update workflow state in session
        try:
            workflow_state = session.get('workflow_state', {})
            workflow_state['requirements_doc_id'] = document.id
            session['workflow_state'] = workflow_state
            current_app.logger.info("Workflow state updated")
        except Exception as e:
            current_app.logger.error(f"Session error: {str(e)}")
            return jsonify({'error': f'Session error: {str(e)}'}), 500
        
        current_app.logger.info(f"Successfully uploaded requirements document: {filename}")
        return jsonify({
            'success': True,
            'document_id': document.id,
            'filename': filename
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error while uploading file: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except IOError as e:
        current_app.logger.error(f"I/O error while saving file: {str(e)}")
        return jsonify({'error': f'I/O error: {str(e)}'}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error while uploading file: {str(e)}")
        current_app.logger.error(f"Error type: {type(e)}")
        current_app.logger.error(f"Error traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

def allowed_file(filename):
    """Check if a filename has an allowed extension"""
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md', 'json'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@chat_bp.route('/insurance/upload-claim', methods=['POST'])
@login_required
def upload_claim():
    try:
        current_app.logger.info("Entering upload_claim function")
        current_app.logger.info(f"UPLOAD_FOLDER configuration: {current_app.config.get('UPLOAD_FOLDER')}")
        
        # Log request information
        current_app.logger.info(f"Request method: {request.method}")
        current_app.logger.info(f"Content type: {request.content_type}")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        
        # Log CSRF token information for debugging
        csrf_token = request.form.get('csrf_token')
        csrf_header = request.headers.get('X-CSRFToken')
        current_app.logger.info(f"CSRF token in form: {bool(csrf_token)}")
        current_app.logger.info(f"CSRF token in header: {bool(csrf_header)}")
        
        workflow_state = session.get('workflow_state', {})
        if not workflow_state.get('requirements_doc_id'):
            current_app.logger.warning("Attempt to upload claim without requirements document")
            return jsonify({'error': 'Please upload requirements document first'}), 400

        reuse_doc_id = request.form.get('reuse_document_id')
        if reuse_doc_id:
            current_app.logger.info(f"Attempting to reuse document with ID: {reuse_doc_id}")
            document = Document.query.get(reuse_doc_id)
            if not document or document.user_id != current_user.id:
                current_app.logger.warning(f"Unauthorized access to document {reuse_doc_id} by user {current_user.id}")
                return jsonify({'error': 'Unauthorized access to document'}), 403
            
            workflow_state['claim_doc_id'] = document.id
            session['workflow_state'] = workflow_state
            current_app.logger.info(f"Successfully reused document: {document.filename}")
            return jsonify({
                'success': True,
                'document_id': document.id,
                'filename': document.filename
            })
        
        current_app.logger.info("Checking for file in request")
        current_app.logger.info(f"Request files: {list(request.files.keys())}")
        current_app.logger.info(f"Request form: {list(request.form.keys())}")
        
        if 'file' not in request.files:
            current_app.logger.warning("No file provided in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not file.filename:
            current_app.logger.warning("No file selected")
            return jsonify({'error': 'No file selected'}), 400

        current_app.logger.info(f"File received: {file.filename}")
        
        # Validate file
        if not allowed_file(file.filename):
            current_app.logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type'}), 400

        # Ensure upload directory exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            current_app.logger.info(f"Creating upload directory: {upload_folder}")
            os.makedirs(upload_folder)
        
        # Save file and create document record
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        current_app.logger.info(f"Saving file to: {file_path}")
        
        try:
            file.save(file_path)
            current_app.logger.info("File saved successfully")
        except Exception as e:
            current_app.logger.error(f"Error saving file: {str(e)}")
            return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
        
        try:
            # Process the file based on its type
            if filename.lower().endswith('.pdf'):
                content = extract_text_from_pdf(file_path)
            else:
                # For text files, read the content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # If UTF-8 fails, try reading as binary
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
            
            document = Document(
                user_id=current_user.id,
                filename=filename,
                file_path=file_path,
                content=content,
                processing_type='insurance_claim'
            )
            db.session.add(document)
            db.session.commit()
            current_app.logger.info("Document record created in database")
            
            workflow_state['claim_doc_id'] = document.id
            session['workflow_state'] = workflow_state
            current_app.logger.info("Workflow state updated")
            
            return jsonify({
                'success': True,
                'document_id': document.id,
                'filename': filename
            })
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error: {str(e)}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error while uploading file: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except IOError as e:
        current_app.logger.error(f"I/O error while saving file: {str(e)}")
        return jsonify({'error': f'I/O error: {str(e)}'}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error while uploading file: {str(e)}")
        current_app.logger.error(f"Error type: {type(e)}")
        current_app.logger.error(f"Error traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

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

        # Map frontend analysis types to backend types
        analysis_type_map = {
            'explain': 'explain',
            'enhance': 'enhance',
            'mock_rejection': 'mock_rejection',
            'language': 'language'
        }
        
        backend_analysis_type = analysis_type_map.get(analysis_type)
        if not backend_analysis_type:
            return jsonify({'error': f'Invalid analysis type: {analysis_type}'}), 400

        # Log the analysis request
        current_app.logger.info(f"Starting analysis - Type: {backend_analysis_type}")
        current_app.logger.info(f"Requirements Doc ID: {workflow_state['requirements_doc_id']}")
        current_app.logger.info(f"Claim Doc ID: {workflow_state['claim_doc_id']}")

        # Get previous chat ID if this is a follow-up analysis
        previous_chat_id = request.form.get('previous_chat_id')
        previous_messages = []
        if previous_chat_id:
            previous_messages = Message.query.filter_by(chat_id=previous_chat_id).order_by(Message.created_at).all()
            previous_messages = [{"role": msg.role, "content": msg.content} for msg in previous_messages]

        chat = Chat(user_id=current_user.id, title=f"Insurance Analysis - {backend_analysis_type}")
        db.session.add(chat)

        claim_doc = Document.query.get_or_404(workflow_state['claim_doc_id'])
        req_doc = Document.query.get_or_404(workflow_state['requirements_doc_id'])

        current_app.logger.info(f"Retrieved documents - Claim: {claim_doc.filename}, Requirements: {req_doc.filename}")

        try:
            analysis_result = analyze_insurance_claim(
                claim_doc.content,
                req_doc.content,
                backend_analysis_type,
                previous_messages if previous_messages else None
            )
            current_app.logger.info("Analysis completed successfully")
            current_app.logger.debug(f"Analysis result: {json.dumps(analysis_result, indent=2)}")
        except Exception as e:
            current_app.logger.error(f"Error in analyze_insurance_claim: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

        claim = InsuranceClaim(
            user_id=current_user.id,
            requirement_id=workflow_state['requirements_doc_id'],
            document_id=workflow_state['claim_doc_id'],
            analysis_type=backend_analysis_type,
            analysis_result=analysis_result
        )
        db.session.add(claim)

        message = Message(
            chat_id=chat.id,
            content=json.dumps(analysis_result, indent=2),
            role='assistant'
        )
        db.session.add(message)
        
        try:
            db.session.commit()
            current_app.logger.info("Saved analysis results to database")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to save analysis results'}), 500

        # Clear workflow state after analysis
        session.pop('workflow_state', None)

        return jsonify({
            'success': True,
            'chat_id': chat.id,
            'message': 'Analysis completed successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error in analyze_documents: {str(e)}")
        db.session.rollback()  # Rollback any pending changes
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
    
    # Get all user's chats for the sidebar
    user_chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.created_at.desc()).all()
    
    return render_template('chat/detail.html', 
                         chat=chat, 
                         messages=messages,
                         chats=user_chats)

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
            model="gpt-4o",
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

@chat_bp.route('/api/abbot/send_message', methods=['POST'])
@login_required
def send_abbot_message():
    chat_id = request.json.get('chat_id')
    content = request.json.get('content')
    
    context_manager = ContextManager(chat_id)
    user_message = context_manager.add_message(content, 'user')
    
    # TODO: Process with AI and get response
    ai_response = "This is a placeholder Abbot AI response."
    ai_message = context_manager.add_message(ai_response, 'assistant')
    
    return jsonify({
        'user_message': user_message.to_dict(),
        'ai_message': ai_message.to_dict()
    })