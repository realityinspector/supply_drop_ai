import os
import json
from openai import OpenAI
from flask import Flask, render_template, request, redirect, flash
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from PyPDF2 import PdfFileReader
import bleach

# ------------------------------------------------------------------------
# SETUP FLASK APP & CONFIG
# ------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'YOUR-DEFAULT-SECRET-KEY')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', './uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit for uploads

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
    openai_key = StringField('OpenAI API Key', validators=[DataRequired()], default=os.getenv('OPENAI_API_KEY'))
    submit = SubmitField('Use Key')

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
        reader = PdfFileReader(pdf_file)
        extracted_text = ""
        for page in range(reader.getNumPages()):
            text = reader.getPage(page).extractText() or ""
            text = bleach.clean(text)  # sanitize text
            extracted_text += text + "\n"
        return True, extracted_text.strip()
    except Exception as e:
        return False, f"Error processing {pdf_file.filename}: {str(e)}"

# Load prompts
RESOURCE_FINDER_PROMPT = load_json_prompt('resource_finder_prompt.json', "You are a helpful assistant trained on wildfire relief resources for Los Angeles.")
REJECTION_SIMULATION_PROMPT = load_json_prompt('rejection_simulation_prompt.json', "You are a harsh simulator that rejects applications for insurance, FEMA, or grants for hurricane and wildfire recovery.")

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
            return "Please enter a question", 400

        try:
            # Initialize OpenAI client with form API key
            client = OpenAI(api_key=form.openai_key.data)

            # Make API call using new client format
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": RESOURCE_FINDER_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )

            # Extract and return the response
            chatbot_answer = response.choices[0].message.content
            return chatbot_answer

        except Exception as e:
            app.logger.error(f"OpenAI API Error: {str(e)}")
            return f"An error occurred: {str(e)}", 500

    return render_template("resource_finder.html", form=form)

@app.route("/rejection-simulation", methods=['GET', 'POST'])
def rejection_simulation():
    """
    Rejection Simulation tool for insurance, FEMA, or grant applications
    """
    form = OpenAIKeyForm()
    simulation_result = None

    if form.validate_on_submit():
        user_message = request.form.get('user_message', '').strip()

        # Process uploaded files
        uploaded_files = request.files.getlist('pdf_files')
        pdf_context = ""

        if len(uploaded_files) > 5:
            flash('Maximum 5 files allowed.', 'error')
            return render_template(
                "rejection_simulation.html",
                form=form,
                simulation_result=None
            )

        # Process each uploaded file
        for pdf_file in uploaded_files:
            if pdf_file and pdf_file.filename:
                if not allowed_file(pdf_file.filename):
                    flash(f'Invalid file type: {pdf_file.filename}. Only PDF files are allowed.', 'error')
                    continue

                success, result = extract_and_clean_pdf_text(pdf_file)
                if success:
                    pdf_context += f"\nContent from {pdf_file.filename}:\n{result}\n"
                else:
                    flash(result, 'error')

        # Combine user message and PDF content
        full_message = user_message
        if pdf_context:
            full_message = f"Application Details:\n{user_message}\n\nSupporting Documents:\n{pdf_context}"

        if full_message:
            try:
                # Initialize OpenAI client with form API key
                client = OpenAI(api_key=form.openai_key.data)
                
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": REJECTION_SIMULATION_PROMPT},
                        {"role": "user", "content": full_message}
                    ],
                    temperature=0.7
                )
                simulation_result = response.choices[0].message.content
            except Exception as e:
                flash(f'Error processing request: {str(e)}', 'error')

    return render_template(
        "rejection_simulation.html",
        form=form,
        simulation_result=simulation_result
    )

# ------------------------------------------------------------------------
# RUN THE APP
# ------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
