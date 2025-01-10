from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
from models import db, FEMAForm, FEMARequirement, FEMAAnalysis
from document_processor import process_fema_document
from auth import login_required

fema_bp = Blueprint('fema', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@fema_bp.route('/fema/wizard')
@login_required
def fema_wizard():
    return render_template('fema/wizard.html', progress=0)

@fema_bp.route('/fema/upload-requirements', methods=['GET', 'POST'])
@login_required
def upload_fema_requirements():
    if request.method == 'GET':
        return render_template('fema/step1_requirements.html', progress=33)
    
    print("Received POST request for file upload")  # Debug log
    
    if 'file' not in request.files:
        print("No file in request.files")  # Debug log
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        print("Empty filename")  # Debug log
        return jsonify({'error': 'No file selected'}), 400
        
    if not allowed_file(file.filename):
        print(f"Invalid file type: {file.filename}")  # Debug log
        return jsonify({'error': 'Invalid file type. Please upload a PDF, DOCX, or TXT file.'}), 400

    try:
        # Create upload folder if it doesn't exist
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file with secure filename
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        print(f"Saving file to: {filepath}")  # Debug log
        file.save(filepath)

        # Create new FEMA form entry
        fema_form = FEMAForm(
            user_id=current_user.id,
            form_type='requirements',
            status='in_progress'
        )
        db.session.add(fema_form)
        db.session.flush()

        print(f"Processing document: {filepath}")  # Debug log
        # Process requirements document
        try:
            requirements = process_fema_document(filepath, 'requirements')
            print(f"Extracted requirements: {requirements}")  # Debug log
        except Exception as e:
            print(f"Error processing document: {str(e)}")  # Debug log
            return jsonify({'error': f'Error processing document: {str(e)}'}), 500
        
        # Create requirement entries
        for req in requirements:
            requirement = FEMARequirement(
                fema_form_id=fema_form.id,
                requirement_text=req,
                is_met=False
            )
            db.session.add(requirement)

        db.session.commit()
        print("Successfully processed file and saved requirements")  # Debug log
        
        return jsonify({
            'success': True,
            'form_id': fema_form.id,
            'requirements': requirements
        })

    except Exception as e:
        print(f"Error in upload process: {str(e)}")  # Debug log
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@fema_bp.route('/fema/upload-form', methods=['POST'])
@login_required
def upload_fema_form():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    form_id = request.form.get('form_id')
    if not form_id:
        return jsonify({'error': 'No form ID provided'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        fema_form = FEMAForm.query.get(form_id)
        if not fema_form or fema_form.user_id != request.user.id:
            return jsonify({'error': 'Invalid form ID'}), 404

        # Process the FEMA form
        analysis_result = process_fema_document(filepath, 'form')
        
        # Update form status
        fema_form.status = 'submitted'
        db.session.commit()

        return jsonify({
            'success': True,
            'analysis': analysis_result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fema_bp.route('/fema/analyze', methods=['POST'])
@login_required
def analyze_fema_form():
    form_id = request.json.get('form_id')
    analysis_type = request.json.get('analysis_type')
    
    if not form_id or not analysis_type:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        fema_form = FEMAForm.query.get(form_id)
        if not fema_form or fema_form.user_id != request.user.id:
            return jsonify({'error': 'Invalid form ID'}), 404

        # Perform analysis
        analysis_result = process_fema_document(None, analysis_type, form_id=form_id)
        
        # Store analysis results
        analysis = FEMAAnalysis(
            fema_form_id=form_id,
            analysis_type=analysis_type,
            content=analysis_result
        )
        db.session.add(analysis)
        db.session.commit()

        return jsonify({
            'success': True,
            'analysis': analysis_result
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 