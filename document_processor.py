import os
from openai import OpenAI
import PyPDF2
from docx import Document as DocxDocument
import io
import json

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
client = OpenAI()

def process_document(file, processing_type='text'):
    """Process document with specified processing type."""
    filename = file.filename.lower()
    
    # Extract raw text content
    if filename.endswith('.pdf'):
        content = process_pdf(file)
    elif filename.endswith('.docx'):
        content = process_docx(file)
    elif filename.endswith('.txt'):
        content = process_txt(file)
    else:
        raise ValueError("Unsupported file format")
    
    # Process content based on type
    if processing_type == 'text':
        return {'raw_text': content, 'processed_text': content}
    elif processing_type == 'summary':
        return process_summary(content)
    elif processing_type == 'analysis':
        return process_analysis(content)
    else:
        raise ValueError("Unsupported processing type")

def process_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def process_docx(file):
    doc = DocxDocument(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def process_txt(file):
    return file.read().decode('utf-8')

def process_summary(content):
    """Generate a summary of the document using OpenAI."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following document content concisely while maintaining key points. Provide the response in JSON format with 'summary' and 'key_points' fields."
                },
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise Exception(f"Failed to generate summary: {str(e)}")

def process_analysis(content):
    """Analyze the document content using OpenAI."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Analyze the following document content and provide insights. Include sentiment, main themes, and key findings. Respond in JSON format with 'sentiment', 'themes', and 'findings' fields."
                },
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise Exception(f"Failed to analyze content: {str(e)}")
