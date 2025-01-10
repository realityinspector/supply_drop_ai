# FEMA Forms Wizard MVP Design Plan

## Overview
This design plan outlines the creation of a FEMA Forms Wizard, replicating the functionality of the existing Insurance Wizard. The MVP will focus on essential features to get the system working quickly.

## Models

Add the following models to `models.py`:

```python
class FEMAForm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    form_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='in_progress')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FEMARequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fema_form_id = db.Column(db.Integer, db.ForeignKey('fema_form.id'), nullable=False)
    requirement_text = db.Column(db.Text, nullable=False)
    is_met = db.Column(db.Boolean, default=False)

class FEMAAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fema_form_id = db.Column(db.Integer, db.ForeignKey('fema_form.id'), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## Routes

Create a new file `fema.py` with the following routes:

```python
from flask import Blueprint, render_template, request, jsonify
from models import db, FEMAForm, FEMARequirement, FEMAAnalysis
from document_processor import process_fema_document

fema_bp = Blueprint('fema', __name__)

@fema_bp.route('/fema/wizard')
def fema_wizard():
    return render_template('fema/wizard.html')

@fema_bp.route('/fema/upload-requirements', methods=['POST'])
def upload_fema_requirements():
    # Handle file upload and processing
    # Create FEMAForm and FEMARequirement entries
    pass

@fema_bp.route('/fema/upload-form', methods=['POST'])
def upload_fema_form():
    # Handle FEMA form upload and processing
    pass

@fema_bp.route('/fema/analyze', methods=['POST'])
def analyze_fema_form():
    # Perform analysis on the FEMA form
    # Create FEMAAnalysis entry
    pass

# Add the blueprint to app.py
# from fema import fema_bp
# app.register_blueprint(fema_bp)
```

## Templates

Create the following templates in the `templates/fema/` directory:

1. `base_fema.html`: Base template for FEMA wizard pages
2. `wizard.html`: Main wizard interface
3. `step1_requirements.html`: Upload FEMA requirements
4. `step2_form.html`: Upload FEMA form
5. `step3_analysis.html`: Display analysis results

## JavaScript

Create a new file `static/js/fema-workflow.js`:

```javascript
// FEMA form upload and processing
function uploadFEMARequirements() {
    // Handle FEMA requirements file upload
}

function uploadFEMAForm() {
    // Handle FEMA form file upload
}

function analyzeFEMAForm() {
    // Trigger FEMA form analysis
}

// Add event listeners and implement the wizard flow
```

## Document Processing

Update `document_processor.py` to include FEMA-specific processing:

```python
def process_fema_document(file_path, analysis_type):
    # Implement FEMA document processing logic
    # Use existing document processing functions as a base
    pass
```

## AI System Prompts

Update `prompts.json` to include FEMA-specific prompts:

```json
{
  "fema_form_explanation": "Analyze the following FEMA form and provide 25 key points...",
  "fema_form_enhancement": "Based on the provided FEMA form, suggest 25 additional items...",
  "fema_form_rejection_analysis": "Identify 25 potential reasons for rejection in the FEMA form...",
  "fema_form_language_review": "Review the language and structure of the FEMA form..."
}
```

## Implementation Steps

1. Update `models.py` with the new FEMA-related models.
2. Create `fema.py` and implement the routes.
3. Create the FEMA-specific templates in `templates/fema/`.
4. Implement `fema-workflow.js` for frontend interactions.
5. Update `document_processor.py` with FEMA document processing logic.
6. Add FEMA-specific prompts to `prompts.json`.
7. Update `app.py` to include the new FEMA blueprint.
8. Test the FEMA Forms Wizard flow end-to-end.

## Next Steps (Post-MVP)

1. Implement user authentication for FEMA form submissions.
2. Add form validation and error handling.
3. Create a dashboard for users to track their FEMA form submissions.
4. Implement document storage and retrieval for submitted FEMA forms.
5. Add email notifications for form status updates. 