from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from extensions import db
from models import User, Report, Chat, Document
from datetime import datetime
import json

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
@login_required
def view_profile():
    """Display user profile page"""
    return render_template('profile/view.html', user=current_user)

@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json()
        current_user.update_profile(data)
        current_user.last_login = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@profile_bp.route('/profile/reports')
@login_required
def list_reports():
    """List all reports for the current user"""
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template('profile/reports.html', reports=reports)

@profile_bp.route('/profile/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate a new custom report"""
    try:
        data = request.get_json()
        report_type = data.get('report_type')
        
        if report_type == 'activity':
            content = generate_activity_report(current_user.id)
        elif report_type == 'document':
            content = generate_document_report(current_user.id)
        elif report_type == 'chat':
            content = generate_chat_report(current_user.id)
        else:
            return jsonify({'error': 'Invalid report type'}), 400

        report = Report(
            user_id=current_user.id,
            title=f"{report_type.capitalize()} Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
            report_type=report_type,
            content=content
        )
        db.session.add(report)
        db.session.commit()

        return jsonify({
            'message': 'Report generated successfully',
            'report_id': report.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def generate_activity_report(user_id):
    """Generate user activity report"""
    chats = Chat.query.filter_by(user_id=user_id).count()
    documents = Document.query.filter_by(user_id=user_id).count()
    
    return {
        'total_chats': chats,
        'total_documents': documents,
        'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
        'credits_remaining': current_user.credits
    }

def generate_document_report(user_id):
    """Generate document analysis report"""
    documents = Document.query.filter_by(user_id=user_id).all()
    return {
        'total_documents': len(documents),
        'documents_by_type': {
            'text': sum(1 for d in documents if d.processing_type == 'text'),
            'insurance_requirements': sum(1 for d in documents if d.processing_type == 'insurance_requirements'),
            'insurance_claim': sum(1 for d in documents if d.processing_type == 'insurance_claim')
        },
        'recent_documents': [
            {
                'filename': doc.filename,
                'type': doc.processing_type,
                'status': doc.processing_status,
                'uploaded_at': doc.uploaded_at.isoformat()
            }
            for doc in documents[-5:]  # Last 5 documents
        ]
    }

def generate_chat_report(user_id):
    """Generate chat interaction report"""
    chats = Chat.query.filter_by(user_id=user_id).all()
    
    return {
        'total_chats': len(chats),
        'recent_chats': [
            {
                'title': chat.title,
                'created_at': chat.created_at.isoformat(),
                'message_count': len(chat.messages)
            }
            for chat in chats[-5:]  # Last 5 chats
        ]
    }
