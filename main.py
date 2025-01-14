import os
import json
from openai import OpenAI
from flask import Flask, render_template, request, redirect, flash, jsonify
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, SubmitField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Optional
from werkzeug.utils import secure_filename
from pypdf import PdfReader
import bleach
import logging

# ------------------------------------------------------------------------
# SETUP FLASK APP & CONFIG
# ------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'YOUR-DEFAULT-SECRET-KEY')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', './uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit for uploads

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Enable CSRF Protection
csrf = CSRFProtect(app)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure OpenAI

# ------------------------------------------------------------------------
# SIMPLE FORM FOR OPENAI KEY (using Flask-WTF)
# ------------------------------------------------------------------------
class OpenAIKeyForm(FlaskForm):
    openai_key = StringField('OpenAI API Key', validators=[Optional()], default=os.getenv('OPENAI_API_KEY'))
    submit = SubmitField('Use Key')

class RejectionSimulationForm(FlaskForm):
    openai_key = StringField('OpenAI API Key', validators=[Optional()], default=os.getenv('OPENAI_API_KEY'))
    user_message = TextAreaField('Describe Your Situation', validators=[DataRequired()])
    documents = MultipleFileField('Supporting Documents')
    submit = SubmitField('Start Simulation')

# ------------------------------------------------------------------------
# HELPER FUNCTIONS FOR LOADING PROMPTS AND PROCESSING FILES
# ------------------------------------------------------------------------
def load_json_prompt(file_path, default_prompt):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('system_prompt', default_prompt)
    except FileNotFoundError:
        return default_prompt

def extract_and_clean_pdf_text(pdf_file):
    """
    Extracts text from a PDF file and sanitizes it.
    Returns tuple of (success, text/error_message)
    """
    try:
        logger.debug(f"Starting to process PDF file: {pdf_file.filename}")

        # Save the file temporarily to handle streaming issues
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pdf_file.filename))
        pdf_file.save(temp_path)

        logger.debug(f"Saved temp file to: {temp_path}")

        # Open the saved file using updated PyPDF2 API
        try:
            with open(temp_path, 'rb') as file:
                from PyPDF2 import PdfReader  # Updated import
                reader = PdfReader(file)
                extracted_text = ""

                logger.debug(f"PDF has {len(reader.pages)} pages")

                for page in reader.pages:
                    text = page.extract_text() or ""  # Updated method name
                    text = bleach.clean(text)  # sanitize text
                    extracted_text += text + "\n"
                    logger.debug(f"Extracted page text length: {len(text)} characters")

                logger.debug(f"Total extracted text length: {len(extracted_text)}")
                if len(extracted_text.strip()) == 0:
                    logger.warning("Warning: Extracted text is empty")
                    return False, "No text could be extracted from the PDF"

                return True, extracted_text.strip()
        except Exception as e:
            logger.error(f"PDF reading error: {str(e)}")
            return False, f"Error reading PDF: {str(e)}"
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_file.filename}: {str(e)}")
        return False, f"Error processing {pdf_file.filename}: {str(e)}"
    finally:
        # Ensure temp file is cleaned up even if there's an error
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.debug(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temp file: {str(e)}")

# Load prompts
RESOURCE_FINDER_PROMPT = load_json_prompt('resource_finder_prompt.json', "You are a helpful assistant trained on wildfire relief resources for Los Angeles.")
REJECTION_SIMULATION_PROMPT = load_json_prompt('rejection_simulation_prompt.json', "You are a harsh simulator that rejects applications for insurance, FEMA, or grants for hurricane and wildfire recovery.")
TOXICITY_ASSESSMENT_PROMPT = load_json_prompt('toxicity_assessment_prompt.json', "You are an expert environmental health specialist helping assess toxicity exposure risks.")

# ------------------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------------------
@app.route("/", methods=['GET', 'POST'])
def index():
    """
    Landing page
    """
    return render_template("index.html")

@app.route("/resource-finder", methods=['GET', 'POST'])
def resource_finder():
    """
    Resource Finder tool for wildfire relief resources in Los Angeles
    """
    form = OpenAIKeyForm()

    if request.method == 'GET':
        return render_template("resource_finder.html", form=form)

    if form.validate_on_submit():
        user_message = request.form.get('user_message', '').strip()
        if not user_message:
            return jsonify({"error": "Please enter a question"}), 400

        try:
            # Initialize OpenAI client with form API key
            api_key = form.openai_key.data or os.getenv('OPENAI_API_KEY')
            client = OpenAI(api_key=api_key)

            # Make API call using new client format
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": RESOURCE_FINDER_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )

            # Extract and return the response
            chatbot_answer = response.choices[0].message.content
            return jsonify({"answer": chatbot_answer})

        except Exception as e:
            app.logger.error(f"OpenAI API Error: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return render_template("resource_finder.html", form=form)

@app.route("/rejection-simulation", methods=['GET', 'POST'])
def rejection_simulation():
    """
    Rejection Simulation tool for insurance, FEMA, or grant applications
    """
    form = RejectionSimulationForm()

    if request.method == 'GET':
        return render_template("rejection_simulation.html", form=form)

    if form.validate_on_submit():
        user_message = form.user_message.data.strip()
        if not user_message:
            return jsonify({"error": "Please describe your situation"}), 400

        # Process uploaded files
        uploaded_files = request.files.getlist('documents')
        documents_context = []

        logger.debug(f"Received {len(uploaded_files)} files")

        if len(uploaded_files) > 5:
            return jsonify({"error": "Maximum 5 files allowed."}), 400

        # Process each uploaded file
        for pdf_file in uploaded_files:
            if pdf_file and pdf_file.filename:
                logger.debug(f"Processing file: {pdf_file.filename}")

                if not allowed_file(pdf_file.filename):
                    return jsonify({"error": f"Invalid file type: {pdf_file.filename}. Only PDF files are allowed."}), 400

                success, result = extract_and_clean_pdf_text(pdf_file)
                if success:
                    logger.debug(f"Successfully extracted text from {pdf_file.filename}, length: {len(result)}")
                    logger.debug(f"First 500 characters of extracted text: {result[:500]}")
                    documents_context.append({
                        "filename": pdf_file.filename,
                        "content": result
                    })
                else:
                    logger.error(f"Failed to extract text: {result}")
                    return jsonify({"error": result}), 400

        # Construct a detailed prompt that clearly separates the application details and documents
        full_message = f"""Application Details:
{user_message}

"""
        if documents_context:
            full_message += "Submitted Documents:\n"
            for doc in documents_context:
                logger.debug(f"Adding document to prompt: {doc['filename']}, content length: {len(doc['content'])}")
                full_message += f"\n--- Document: {doc['filename']} ---\n{doc['content']}\n"
        else:
            full_message += "\nNote: No supporting documents were provided with this application."

        # Log the complete payload being sent to OpenAI
        openai_payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": REJECTION_SIMULATION_PROMPT},
                {"role": "user", "content": full_message}
            ],
            "temperature": 0.7
        }
        logger.debug("Complete OpenAI payload:")
        logger.debug(json.dumps(openai_payload, indent=2))

        try:
            # Initialize OpenAI client with form API key
            api_key = form.openai_key.data or os.getenv('OPENAI_API_KEY')
            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": REJECTION_SIMULATION_PROMPT},
                    {"role": "user", "content": full_message}
                ],
                temperature=0.7
            )
            simulation_result = response.choices[0].message.content
            logger.debug("Received OpenAI response:")
            logger.debug(simulation_result)
            return jsonify({"answer": simulation_result})

        except Exception as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # If form validation failed
    return jsonify({"error": "Invalid form submission"}), 400
    

@app.route("/legal")
def legal():
    """
    Combined Terms of Use and Privacy Policy page
    """
    return render_template("legal.html")

@app.route("/toxicity-assessment", methods=['GET', 'POST'])
def toxicity_assessment():
    """
    Toxicity Assessment tool for evaluating environmental exposure risks
    """
    form = OpenAIKeyForm()

    if request.method == 'GET':
        return render_template("toxicity_assessment.html", form=form)

    if form.validate_on_submit():
        user_message = request.form.get('user_message', '').strip()
        message_history = request.form.get('message_history', '[]')
        
        if not user_message:
            return jsonify({"error": "Please enter your response"}), 400

        try:
            # Parse message history
            message_history = json.loads(message_history)
            
            # Initialize OpenAI client with form API key
            api_key = form.openai_key.data or os.getenv('OPENAI_API_KEY')
            client = OpenAI(api_key=api_key)

            # Construct messages array with system prompt and history
            messages = [
                {"role": "system", "content": TOXICITY_ASSESSMENT_PROMPT}
            ]
            messages.extend(message_history)

            # Make API call using new client format
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7
            )

            # Extract and return the response
            chatbot_answer = response.choices[0].message.content
            return jsonify({"answer": chatbot_answer})

        except json.JSONDecodeError:
            app.logger.error("Failed to parse message history")
            return jsonify({"error": "Invalid message history format"}), 400
        except Exception as e:
            app.logger.error(f"OpenAI API Error: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return render_template("toxicity_assessment.html", form=form)

# ------------------------------------------------------------------------
# RUN THE APP
# ------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)