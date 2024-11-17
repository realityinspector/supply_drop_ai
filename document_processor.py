import os
import json
from openai import OpenAI
import PyPDF2
from docx import Document as DocxDocument
import io
from typing import Dict, Any, List
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
client = OpenAI()

def process_document(file, processing_type='text') -> Dict[str, Any]:
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

def process_pdf(file) -> str:
    """Extract text from PDF files."""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error processing PDF: {str(e)}")

def process_docx(file) -> str:
    """Extract text from DOCX files."""
    try:
        doc = DocxDocument(io.BytesIO(file.read()))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error processing DOCX: {str(e)}")

def process_txt(file) -> str:
    """Extract text from TXT files."""
    try:
        return file.read().decode('utf-8').strip()
    except Exception as e:
        raise ValueError(f"Error processing TXT: {str(e)}")

def process_summary(content: str) -> Dict[str, Any]:
    """Generate a summary of the document using OpenAI."""
    try:
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="""Summarize the following document content concisely while maintaining key points.
                Provide the response in this JSON format:
                {
                    "raw_text": "original text",
                    "summary": "concise summary",
                    "key_points": ["point 1", "point 2", ...],
                    "metadata": {
                        "word_count": "number of words in original",
                        "summary_length": "number of words in summary",
                        "compression_ratio": "percentage of reduction"
                    }
                }"""
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=content
            )
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return json.loads(response.choices[0].message.content)
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to generate summary: {str(e)}")

def process_analysis(content: str) -> Dict[str, Any]:
    """Analyze the document content using OpenAI."""
    try:
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="""Analyze the following document content and provide detailed insights.
                Include sentiment, main themes, key findings, and readability metrics.
                Respond in this JSON format:
                {
                    "raw_text": "original text",
                    "analysis": {
                        "sentiment": {
                            "overall": "positive/negative/neutral",
                            "confidence": 0.0-1.0,
                            "key_phrases": ["phrase 1", "phrase 2"]
                        },
                        "themes": ["theme1", "theme2", ...],
                        "findings": ["finding1", "finding2", ...],
                        "readability": {
                            "score": "0-100",
                            "grade_level": "reading grade level",
                            "suggestions": ["suggestion1", "suggestion2"]
                        }
                    }
                }"""
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=content
            )
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return json.loads(response.choices[0].message.content)
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to analyze content: {str(e)}")

def process_insurance_requirements(content: str) -> Dict[str, Any]:
    """Extract and analyze insurance requirements using OpenAI."""
    try:
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="""Extract and analyze insurance requirements from the document.
                For each requirement, identify:
                - The specific requirement text
                - Category (e.g., liability, property, health, auto)
                - Priority level (high, medium, low)
                - Coverage amounts
                - Deadlines or time constraints
                - Special conditions
                
                Respond in this JSON format:
                {
                    "raw_text": "original text",
                    "requirements": [
                        {
                            "requirement_text": "string",
                            "category": "string",
                            "priority": "string",
                            "coverage": {
                                "amount": "string",
                                "type": "string"
                            },
                            "deadline": "string or null",
                            "conditions": ["condition1", "condition2"],
                            "compliance_score": 0-100
                        }
                    ],
                    "summary": {
                        "total_requirements": 0,
                        "priority_breakdown": {
                            "high": 0,
                            "medium": 0,
                            "low": 0
                        },
                        "categories": ["category1", "category2"]
                    }
                }"""
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=content
            )
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return json.loads(response.choices[0].message.content)
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to process insurance requirements: {str(e)}")

def analyze_insurance_claim(claim_content: str, requirement_content: str, analysis_type: str) -> Dict[str, Any]:
    """Analyze insurance claim against requirements with specified analysis type."""
    try:
        system_prompts = {
            'critique': """Critically evaluate this claim against the requirements.
                       Identify gaps, inconsistencies, and areas of concern.
                       Provide specific recommendations for improvement.""",
            'enhance': """Analyze this claim and suggest enhancements.
                       Consider industry best practices and successful claim patterns.
                       Provide actionable suggestions for strengthening the claim.""",
            'formalize': """Rewrite this claim in formal, professional insurance language.
                         Ensure compliance with standard insurance terminology and format.
                         Maintain all key information while improving clarity.""",
            'grammar': """Perform detailed grammar and spelling analysis.
                       Identify and correct errors while maintaining meaning.
                       Suggest improvements for clarity and professionalism."""
        }

        if analysis_type not in system_prompts:
            raise ValueError(f"Invalid analysis type: {analysis_type}")

        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content=f"""{system_prompts[analysis_type]}
                Provide response in this JSON format:
                {{
                    "analysis": {{
                        "summary": "detailed analysis text",
                        "score": 0-100,
                        "recommendations": ["rec1", "rec2", ...],
                        "issues": ["issue1", "issue2", ...],
                        "improvements": {{
                            "high_priority": ["improvement1", "improvement2"],
                            "medium_priority": ["improvement1", "improvement2"],
                            "low_priority": ["improvement1", "improvement2"]
                        }}
                    }},
                    "details": {{
                        "matching_requirements": ["req1", "req2"],
                        "missing_requirements": ["req1", "req2"],
                        "compliance_score": 0-100,
                        "risk_assessment": "string"
                    }}
                }}"""
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"Requirements:\n{requirement_content}\n\nClaim:\n{claim_content}"
            )
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return json.loads(response.choices[0].message.content)
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to analyze insurance claim: {str(e)}")
