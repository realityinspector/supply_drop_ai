import PyPDF2
from docx import Document as DocxDocument
import io

def process_document(file):
    filename = file.filename.lower()
    
    if filename.endswith('.pdf'):
        return process_pdf(file)
    elif filename.endswith('.docx'):
        return process_docx(file)
    elif filename.endswith('.txt'):
        return process_txt(file)
    else:
        raise ValueError("Unsupported file format")

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
