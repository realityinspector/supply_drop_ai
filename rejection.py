import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from openai import OpenAI
from models import Document, db
import PyPDF2
import chardet
import logging
import time

rejection_bp = Blueprint('rejection', __name__)
client = OpenAI()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'md', 'markdown'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from PDF with error handling"""
    text_content = []
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                try:
                    text_content.append(page.extract_text() or '')
                except Exception as e:
                    logger.warning(f"Failed to extract text from PDF page: {e}")
                    continue
    except Exception as e:
        logger.error(f"Failed to process PDF file: {e}")
        return None
    return '\n'.join(text_content)

def read_text_file(file_path):
    """Read text file with encoding detection and error handling"""
    try:
        # First, detect the file encoding
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'

        # Try to read with detected encoding, fallback to utf-8 with error handling
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
    except Exception as e:
        logger.error(f"Failed to read text file: {e}")
        return None

@rejection_bp.route('/')
def index():
    """Show the rejection simulation interface"""
    return render_template('rejection/wizard.html')

@rejection_bp.route('/upload', methods=['POST'])
def upload_document():
    """Handle document upload for rejection analysis"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed types: PDF, TXT, MD, Markdown'}), 400
    
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Save uploaded file
        file.save(file_path)
        
        # Extract content based on file type
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext == 'pdf':
            content = extract_text_from_pdf(file_path)
        else:  # txt, md, markdown
            content = read_text_file(file_path)
        
        # Handle extraction failure
        if content is None or not content.strip():
            return jsonify({
                'error': 'Could not extract content from file. Please ensure it contains readable text.'
            }), 400
        
        # Create temporary document
        doc = Document(
            filename=filename,
            file_path=file_path,
            content=content,
            processing_type='rejection_analysis',
            session_id=session['session_id']
        )
        db.session.add(doc)
        db.session.commit()
        
        # Analyze document
        analysis = analyze_document(content)
        
        # Store analysis in session
        session['current_analysis'] = analysis
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return jsonify({'error': 'Failed to process file. Please try again.'}), 500

def analyze_document(content):
    """Perform rejection analysis on document"""
    system_prompt = """You are an expert insurance analyst. Your task is to analyze the provided insurance document 
    and generate exactly 25 potential reasons for rejection, organized by priority (High, Medium, Low).
    Focus on coverage gaps, compliance issues, and documentation problems.
    If the document appears to be incomplete or unclear, include that as a potential rejection reason."""
    
    try:
        start_time = time.time()
        timeout = 60  # Set a 60-second timeout

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this insurance document for potential rejection reasons:\n\n{content}"}
            ],
            timeout=timeout
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Analysis completed in {elapsed_time:.2f} seconds")

        return {
            'rejection_reasons': response.choices[0].message.content,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        if isinstance(e, TimeoutError):
            return {'error': 'Analysis timed out. Please try again with a shorter document.'}
        else:
            return {'error': f"Analysis failed: {str(e)}"}

@rejection_bp.route('/clear', methods=['POST'])
def clear_session():
    """Clear current analysis from session"""
    if 'current_analysis' in session:
        del session['current_analysis']
    return jsonify({'success': True}) 