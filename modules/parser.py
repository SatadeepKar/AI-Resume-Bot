"""
Resume Parser Module
Extracts structured data from PDF and DOCX resume files using text extraction
and Groq LLM (via OpenAI-compatible API) for intelligent parsing.
"""
import os
import json
from typing import Optional
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader
from docx import Document
from openai import OpenAI

from config import settings


# ── Groq Client ──────────────────────────────────────────────────────────────

def get_llm_client() -> OpenAI:
    """Get Groq client (OpenAI-compatible)."""
    return OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url=settings.GROQ_BASE_URL,
    )


# ── Data Models ──────────────────────────────────────────────────────────────

class Experience(BaseModel):
    title: str = ""
    company: str = ""
    duration: str = ""
    bullets: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""
    gpa: str = ""


class ResumeData(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    raw_text: str = ""


# ── Text Extraction ─────────────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    return "\n".join(text_parts)


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Use PDF or DOCX.")


# ── Structured Extraction via LLM ────────────────────────────────────────────

EXTRACTION_PROMPT = """You are an expert resume parser. Extract structured information from the following resume text.

Return a JSON object with EXACTLY these fields:
{
  "name": "Full name",
  "email": "Email address or empty string",
  "phone": "Phone number or empty string",
  "linkedin": "LinkedIn URL or empty string",
  "summary": "Professional summary or objective if present, otherwise empty string",
  "skills": ["skill1", "skill2", ...],
  "experience": [
    {
      "title": "Job title",
      "company": "Company name",
      "duration": "Duration (e.g., Jan 2020 - Present)",
      "bullets": ["Achievement 1", "Achievement 2"]
    }
  ],
  "projects": [
    {
      "name": "Project name",
      "description": "Brief description",
      "technologies": ["tech1", "tech2"],
      "bullets": ["Detail 1", "Detail 2"]
    }
  ],
  "education": [
    {
      "degree": "Degree name",
      "institution": "Institution name",
      "year": "Graduation year or duration",
      "gpa": "GPA if mentioned, otherwise empty string"
    }
  ],
  "certifications": ["Certification 1", "Certification 2"]
}

IMPORTANT:
- Extract ONLY what is present. Do NOT invent data.
- If a section is not present, return an empty list or empty string.
- Return ONLY valid JSON, no additional text.

Resume text:
"""


def extract_structured_data(raw_text: str) -> ResumeData:
    client = get_llm_client()

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise resume parser. Return only valid JSON."},
            {"role": "user", "content": EXTRACTION_PROMPT + raw_text}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content
    data = json.loads(result_text)

    resume = ResumeData(
        name=data.get("name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        linkedin=data.get("linkedin", ""),
        summary=data.get("summary", ""),
        skills=data.get("skills", []),
        experience=[Experience(**exp) for exp in data.get("experience", [])],
        projects=[Project(**proj) for proj in data.get("projects", [])],
        education=[Education(**edu) for edu in data.get("education", [])],
        certifications=data.get("certifications", []),
        raw_text=raw_text
    )
    return resume


# ── Main Parse Function ─────────────────────────────────────────────────────

def parse_resume(file_path: str) -> ResumeData:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    raw_text = extract_text(file_path)
    if not raw_text.strip():
        raise ValueError("Could not extract any text from the resume file.")

    return extract_structured_data(raw_text)
