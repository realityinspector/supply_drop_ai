import os
import json
from openai import OpenAI
import PyPDF2
from docx import Document as DocxDocument
import io

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
    elif processing_type == 'insurance_requirements':
        return process_insurance_requirements(content)
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
                    "content": """Summarize the following document content concisely while maintaining key points.
                    Provide the response in this JSON format:
                    {
                        "raw_text": "original text",
                        "summary": "concise summary",
                        "key_points": ["point 1", "point 2", ...]
                    }"""
                },
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        raise Exception("Empty response from OpenAI")
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
                    "content": """Analyze the following document content and provide insights.
                    Include sentiment, main themes, and key findings.
                    Respond in this JSON format:
                    {
                        "raw_text": "original text",
                        "sentiment": "positive/negative/neutral",
                        "themes": ["theme1", "theme2", ...],
                        "findings": ["finding1", "finding2", ...]
                    }"""
                },
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to analyze content: {str(e)}")

def process_insurance_requirements(content):
    """Extract insurance requirements from document content using OpenAI."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """Extract insurance requirements from the document and format them as structured data.
                    For each requirement, identify:
                    - The specific requirement text
                    - Category (e.g., liability, property, health, auto)
                    - Priority level (high, medium, low)
                    
                    Respond in this JSON format:
                    {
                        "raw_text": "original text",
                        "requirements": [
                            {
                                "requirement_text": "string",
                                "category": "string",
                                "priority": "string",
                                "details": {}
                            },
                            ...
                        ]
                    }"""
                },
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to process insurance requirements: {str(e)}")

def analyze_insurance_claim(claim_content, requirement_content, analysis_type):
    """Analyze insurance claim against requirements with specified analysis type."""
    try:
        system_prompts = {
            'critique': """As an insurance adjuster, critically evaluate this claim against the requirements.
                         Identify any missing elements, inconsistencies, or areas of concern.
                         Provide specific recommendations for improvement.""",
            'enhance': """Analyze this claim and suggest additional elements that could strengthen it.
                         Consider industry best practices and common successful claim patterns.""",
            'formalize': """Rewrite this claim in formal, professional insurance language while maintaining
                          all key information. Ensure compliance with standard insurance terminology.""",
            'grammar': """Perform a detailed grammar and spelling check of this claim.
                         Identify and correct any errors while maintaining the original meaning."""
        }

        if analysis_type not in system_prompts:
            raise ValueError(f"Invalid analysis type: {analysis_type}")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"""{system_prompts[analysis_type]}
                    Provide response in this JSON format:
                    {{
                        "analysis": "detailed analysis text",
                        "recommendations": ["rec1", "rec2", ...],
                        "score": 0-100,
                        "issues": ["issue1", "issue2", ...]
                    }}"""
                },
                {
                    "role": "user",
                    "content": f"Requirements:\n{requirement_content}\n\nClaim:\n{claim_content}"
                }
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to analyze insurance claim: {str(e)}")
