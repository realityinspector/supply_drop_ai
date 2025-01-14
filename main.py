import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
import bleach
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

# ------------------------------------------------------------------------
# SETUP FLASK APP & CONFIG
# ------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'YOUR-DEFAULT-SECRET-KEY')
csrf = CSRFProtect(app)

# Allow up to two PDF files
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB just as an example
app.config['UPLOAD_EXTENSIONS'] = ['.pdf']

# ------------------------------------------------------------------------
# SIMPLE FORM FOR OPENAI KEY (using Flask-WTF)
# ------------------------------------------------------------------------
class OpenAIKeyForm(FlaskForm):
    openai_key = StringField('OpenAI API Key', validators=[DataRequired()], default=os.getenv('OPENAI_API_KEY'))
    submit = SubmitField('Use Key')
# ------------------------------------------------------------------------
# READ SYSTEM PROMPT FROM JSON (for the first chatbot)
# ------------------------------------------------------------------------
def load_system_prompt_from_json():
    try:
        with open('system_prompt.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('system_prompt', "You are a helpful assistant.")
    except FileNotFoundError:
        return "You are a helpful assistant."

# ------------------------------------------------------------------------
# READ SYSTEM PROMPT FROM PDF (for the PDF-based chatbot)
# ------------------------------------------------------------------------
def load_system_prompt_from_pdf():
    try:
        with open('system_prompt.pdf', 'rb') as f:
            reader = PdfReader(f)
            # Concatenate text from all pages
            prompt_text = ""
            for page in reader.pages:
                page_text = page.extract_text() or ""
                page_text = bleach.clean(page_text)  # sanitize text
                prompt_text += page_text + "\n"
            return prompt_text.strip()
    except FileNotFoundError:
        return "You are a helpful assistant (PDF)."

# ------------------------------------------------------------------------
# PDF TEXT EXTRACTION, CLEANING, AND SANITIZING
# ------------------------------------------------------------------------
def extract_and_clean_pdf_text(pdf_file):
    """
    Extracts text from an uploaded PDF file, sanitizes it with bleach.
    """
    reader = PdfReader(pdf_file)
    extracted_text = ""
    for page in reader.pages:
        text = page.extract_text() or ""
        text = bleach.clean(text)  # basic sanitization
        extracted_text += text + "\n"
    return extracted_text.strip()

# ------------------------------------------------------------------------
# ROUTE: LANDING PAGE
# ------------------------------------------------------------------------
@app.route("/", methods=['GET', 'POST'])
def index():
    """
    Landing page with hero content and links to:
      - /chatbot
      - /chatbot-pdf
    """
    return render_template("index.html")

# ------------------------------------------------------------------------
# ROUTE: SIMPLE CHATBOT (no conversation storing)
# ------------------------------------------------------------------------
@app.route("/chatbot", methods=['GET', 'POST'])
def chatbot():
    """
    A simple page that uses:
      - system_prompt from JSON
      - OpenAI completions
      - Does not store user conversation
    """
    form = OpenAIKeyForm()
    chatbot_answer = None

    if form.validate_on_submit():
        # Grab user input
        user_message = request.form.get('user_message', '')

        # Build the system prompt
        system_prompt = load_system_prompt_from_json()

        # Make the call to OpenAI
        if user_message.strip():
            response = client.chat.completions.create(model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7)
            chatbot_answer = response.choices[0].message.content

    return render_template(
        "chatbot.html",
        form=form,
        chatbot_answer=chatbot_answer
    )

# ------------------------------------------------------------------------
# ROUTE: PDF-BASED CHATBOT
# ------------------------------------------------------------------------
@app.route("/chatbot-pdf", methods=['GET', 'POST'])
def chatbot_pdf():
    """
    A chatbot page that:
      - Accepts up to two PDFs
      - Extracts & cleans PDF text
      - Combines it into the user prompt
      - Fetches system prompt from a PDF (system_prompt.pdf)
      - Uses user's OpenAI API key
    """
    form = OpenAIKeyForm()
    chatbot_answer = None

    if form.validate_on_submit():
        # Set openai key
        user_message = request.form.get('user_message', '')

        # Load system prompt from the system_prompt.pdf
        system_prompt = load_system_prompt_from_pdf()

        # Process up to two PDFs
        uploaded_files = request.files.getlist("pdf_files")
        pdf_context = ""
        for f in uploaded_files:
            if f and f.filename.endswith('.pdf'):
                filename = secure_filename(f.filename)
                pdf_text = extract_and_clean_pdf_text(f)
                pdf_context += pdf_text + "\n\n"

        # Combine PDF text into the user prompt
        # Example: "Here is some context from your PDFs:\n{pdf_context}\nUser message: {user_message}"
        full_user_message = f"PDF Context:\n{pdf_context}\n\nUser Message: {user_message}"

        if user_message.strip() or pdf_context.strip():
            response = client.chat.completions.create(model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user_message}
            ],
            temperature=0.7)
            chatbot_answer = response.choices[0].message.content

    return render_template(
        "chatbot_pdf.html",
        form=form,
        chatbot_answer=chatbot_answer
    )

# ------------------------------------------------------------------------
# RUN THE APP (For Replit, often just `python main.py`)
# ------------------------------------------------------------------------
if __name__ == "__main__":
    # On Replit, it often auto-detects. Otherwise:
    # app.run(host='0.0.0.0', port=8000, debug=True)
    app.run(debug=True)
