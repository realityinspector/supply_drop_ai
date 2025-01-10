import os
import json
from openai import OpenAI
import PyPDF2
from docx import Document as DocxDocument
import io
from typing import Dict, Any, List
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

# Initialize OpenAI client
client = OpenAI()

# Load prompts from JSON file
def load_prompts() -> Dict[str, Any]:
    with open('prompts.json', 'r') as f:
        return json.load(f)

# Global prompts dictionary
PROMPTS = load_prompts()

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
                role=PROMPTS["document_summary"]["role"],
                content=PROMPTS["document_summary"]["content"]
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
                role=PROMPTS["document_analysis"]["role"],
                content=PROMPTS["document_analysis"]["content"]
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
                role=PROMPTS["insurance_requirements"]["role"],
                content=PROMPTS["insurance_requirements"]["content"]
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

def analyze_insurance_claim(claim_content: str, requirement_content: str, analysis_type: str, previous_messages: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """Analyze insurance claim against requirements with specified analysis type."""
    try:
        if analysis_type not in PROMPTS["insurance_analysis"]:
            raise ValueError(f"Invalid analysis type: {analysis_type}")

        # Build context from previous messages if they exist
        context_prompt = ""
        if previous_messages:
            context_prompt = "\nPrevious analyses have already covered these points:\n"
            for msg in previous_messages:
                if msg["role"] == "assistant" and msg.get("content"):
                    try:
                        content = json.loads(msg["content"])
                        if "analysis" in content and "improvements" in content["analysis"]:
                            for priority, items in content["analysis"]["improvements"].items():
                                context_prompt += f"\n{priority}:\n"
                                context_prompt += "\n".join(items) + "\n"
                    except json.JSONDecodeError:
                        continue
            context_prompt += "\nProvide 25 NEW and UNIQUE points that haven't been covered above.\n"

        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role=PROMPTS["insurance_analysis"][analysis_type]["role"],
                content=f"""{PROMPTS["insurance_analysis"][analysis_type]["content"]}
{context_prompt}
Provide your response as exactly 25 NEW items, organized into priority sections but maintaining a sequential numbering from 1-25. Format as follows:

{{
    "analysis": {{
        "summary": "detailed analysis text",
        "score": 0-100,
        "improvements": {{
            "high_priority": [
                "1. First high priority item",
                "2. Second high priority item",
                "3. Third high priority item"
            ],
            "medium_priority": [
                "8. First medium priority item",
                "9. Second medium priority item"
            ],
            "low_priority": [
                "15. First low priority item",
                "16. Second low priority item"
            ]
        }}
    }},
    "details": {{
        "matching_requirements": ["req1", "req2"],
        "missing_requirements": ["req1", "req2"],
        "compliance_score": 0-100,
        "is_followup_analysis": true
    }}
}}

IMPORTANT: 
- Maintain sequential numbering from 1 to 25 across all sections
- Each item should start with its number (1-25) followed by a period
- The total number of items across all priority sections must equal exactly 25
- All items must be NEW and not mentioned in any previous analyses
- Focus on different aspects or deeper details than previous analyses
- Ensure your response is a valid JSON object"""
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"Requirements:\n{requirement_content}\n\nClaim:\n{claim_content}"
            )
        ]

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError as json_error:
                raise ValueError(f"Failed to parse JSON response: {str(json_error)}")
        raise Exception("Empty response from OpenAI")
    except Exception as e:
        raise Exception(f"Failed to analyze insurance claim: {str(e)}")
