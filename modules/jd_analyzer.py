"""
Job Description Analyzer Module
Extracts structured information from job descriptions using Groq LLM.
"""
import json
from pydantic import BaseModel, Field
from openai import OpenAI

from config import settings


def get_llm_client() -> OpenAI:
    return OpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL)


class JDAnalysis(BaseModel):
    title: str = ""
    company: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    priority_keywords: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    experience_level: str = ""
    industry: str = ""


JD_ANALYSIS_PROMPT = """You are an expert job description analyzer. Analyze the following job description and extract structured information.

Return a JSON object with EXACTLY these fields:
{
  "title": "Job title",
  "company": "Company name if mentioned, otherwise empty string",
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["nice-to-have skill1", ...],
  "keywords": ["all important keywords and phrases from the JD"],
  "priority_keywords": ["top 10 most critical keywords a resume MUST have"],
  "responsibilities": ["responsibility1", ...],
  "qualifications": ["qualification1", ...],
  "experience_level": "Entry/Mid/Senior/Lead/Principal",
  "industry": "Industry or domain if identifiable"
}

Be thorough with keywords. Return ONLY valid JSON.

Job Description:
"""


def analyze_jd(jd_text: str) -> JDAnalysis:
    if not jd_text.strip():
        raise ValueError("Job description text is empty.")

    client = get_llm_client()

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise job description analyzer. Return only valid JSON."},
            {"role": "user", "content": JD_ANALYSIS_PROMPT + jd_text}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)

    return JDAnalysis(
        title=data.get("title", ""),
        company=data.get("company", ""),
        required_skills=data.get("required_skills", []),
        preferred_skills=data.get("preferred_skills", []),
        keywords=data.get("keywords", []),
        priority_keywords=data.get("priority_keywords", []),
        responsibilities=data.get("responsibilities", []),
        qualifications=data.get("qualifications", []),
        experience_level=data.get("experience_level", ""),
        industry=data.get("industry", "")
    )
