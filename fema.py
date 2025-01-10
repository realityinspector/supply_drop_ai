from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
from models import db, FEMAForm, FEMARequirement, FEMAAnalysis
from document_processor import process_fema_document
from auth import login_required

fema_bp = Blueprint('fema', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx', 'txt'}

@fema_bp.route('/fema/wizard')
@login_required
def fema_wizard():
    return render_template('fema/wizard.html')

@fema_bp.route('/fema/upload-requirements', methods=['POST'])
@login_required
def upload_fema_requirements():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # Create new FEMA form entry
        fema_form = FEMAForm(
            user_id=request.user.id,
            form_type='requirements',
            status='in_progress'
        )
        db.session.add(fema_form)
        db.session.flush()

        # Process requirements document
        requirements = process_fema_document(filepath, 'requirements')
        
        # Create requirement entries
        for req in requirements:
            requirement = FEMARequirement(
                fema_form_id=fema_form.id,
                requirement_text=req,
                is_met=False
            )
            db.session.add(requirement)

        db.session.commit()
        return jsonify({
            'success': True,
            'form_id': fema_form.id,
            'requirements': requirements
        })

    except Exception as e:
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