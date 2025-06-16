import io
from PyPDF2 import PdfReader
from docx import Document
from typing import Dict, Any, List, Optional
import json

from services.groq_service import GroqService

async def extract_info_with_groq(resume_text: str, groq_service: GroqService) -> Dict[str, Any]:
    """
    Uses the Groq LLM (via GroqService) to extract structured information
    from raw resume text based on a defined JSON schema.
    """
    prompt = f"""
    You are an expert resume parser. Extract the following information from the provided resume text.
    If a field is not found, use a reasonable default (e.g., empty string, empty list) or null.
    Provide the output as a JSON object with the specified keys.

    Resume Text:
    ---
    {resume_text}
    ---

    Required JSON Schema for the output:
    {{
        "name": "string (e.g., John Doe)",
        "email": "string (e.g., john.doe@example.com, nullable)",
        "phone": "string (e.g., +1-123-456-7890, nullable)",
        "experience": "string (A concise summary of total work experience, e.g., '5 years as Software Engineer, 2 years as Team Lead', nullable)",
        "skills": ["list of strings (e.g., Python, React, AWS, can be empty)"],
        "projects": [
            {{"title": "string (title of the project)", "description": "string (concise description of the project and your role, can be empty)"}}
        ],
        "education": "string (e.g., 'M.Sc. Computer Science from XYZ University', nullable)"
    }}
    Ensure the output is valid JSON and strictly adheres to the schema.
    """
    try:
        response_json_str = await groq_service.generate_structured_response(prompt)
        print(f"Raw structured response from LLM for resume parsing: {response_json_str}")

        parsed_data = json.loads(response_json_str)

        result = {
            "name": parsed_data.get("name"),
            "email": parsed_data.get("email"),
            "phone": parsed_data.get("phone"),
            "experience": parsed_data.get("experience", "No experience mentioned."),
            "skills": parsed_data.get("skills", []),
            "projects": parsed_data.get("projects", []),
            "education": parsed_data.get("education"),
        }
        return result
    except json.JSONDecodeError as e:
        print(f"JSON parsing error from LLM response during resume parsing: {e}")
        print(f"Problematic Groq response: {response_json_str}")
        return {
            "name": None, "email": None, "phone": None,
            "experience": "Could not parse experience from resume.",
            "skills": [], "projects": [], "education": None
        }
    except Exception as e:
        print(f"Error during LLM info extraction for resume: {e}")
        return {
            "name": None, "email": None, "phone": None,
            "experience": "Could not extract resume information due to an error.",
            "skills": [], "projects": [], "education": None
        }


def parse_pdf(file_content: bytes) -> str:
    """Parses plain text from a PDF file."""
    reader = PdfReader(io.BytesIO(file_content))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def parse_docx(file_content: bytes) -> str:
    """Parses plain text from a DOCX file."""
    document = Document(io.BytesIO(file_content))
    text = ""
    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"
    return text.strip()

async def parse_resume(file_content: bytes, filename: str, groq_service: GroqService) -> Dict[str, Any]:
    """
    Parses a resume file (PDF or DOCX), extracts raw text, and then
    uses the GroqService to extract structured information from it.
    """
    raw_text = ""
    if filename.endswith(".pdf"):
        raw_text = parse_pdf(file_content)
    elif filename.endswith(".docx"):
        raw_text = parse_docx(file_content)
    else:
        raise ValueError("Unsupported file type. Please upload a PDF or DOCX resume.")

    if not raw_text.strip():
        raise ValueError("Could not extract any text from the provided resume file. Please ensure it's a valid PDF/DOCX with readable text.")

    structured_info = await extract_info_with_groq(raw_text, groq_service)

    structured_info["raw_text"] = raw_text
    return structured_info
