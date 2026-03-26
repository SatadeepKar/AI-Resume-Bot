"""
AI Resume Rewriter Module
Uses Groq LLM (via OpenAI-compatible API) to rewrite resume content
tailored to a job description. Generates 3 distinct versions.
"""
import json
from pydantic import BaseModel, Field
from openai import OpenAI

from config import settings
from modules.parser import ResumeData
from modules.jd_analyzer import JDAnalysis


def get_llm_client() -> OpenAI:
    return OpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL)


class RewrittenResume(BaseModel):
    version_type: str = ""
    version_label: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    preview_text: str = ""


VERSION_CONFIGS = {
    "ats_optimized": {
        "label": "ATS Optimized",
        "system_prompt": """You are an expert ATS resume optimizer. Maximize ATS compatibility.
- Use EXACT keywords from the job description naturally
- Use standard section headings
- Start bullets with strong action verbs
- Include quantifiable achievements
- Add relevant skills from JD that the candidate could reasonably have
- Do NOT invent false experience or fake companies""",
    },
    "modern_professional": {
        "label": "Modern Professional",
        "system_prompt": """You are an expert professional resume writer creating a polished, modern resume.
- Write a compelling professional summary
- Focus on achievements and impact over duties
- Add metrics and quantifiable results
- Balance keyword usage with readability
- Use modern professional tone
- Add relevant skills from JD that the candidate could reasonably have
- Do NOT invent false experience or fake companies""",
    },
    "developer_focused": {
        "label": "Developer / Technical",
        "system_prompt": """You are an expert technical resume writer for developer resumes.
- Lead with technical skills organized by category
- Emphasize technical projects with detailed tech stacks
- Use developer-friendly language
- Highlight system design, scalability, performance
- Make projects section prominent
- Add relevant technologies from JD that align with candidate's background
- Do NOT invent false experience or fake companies""",
    },
}


REWRITE_PROMPT = """Rewrite the following resume for the given job description.

ORIGINAL RESUME:
{resume_json}

JOB DESCRIPTION:
- Title: {jd_title}
- Required Skills: {required_skills}
- Priority Keywords: {priority_keywords}
- Responsibilities: {responsibilities}

INSTRUCTIONS:
1. Keep real name, email, phone, linkedin
2. Rewrite summary to align with target role
3. Enhance bullets with impact, metrics, and JD keywords
4. Update skills to include relevant JD skills matching candidate's background
5. Do NOT invent new companies or false experience

Return a JSON object:
{{
  "name": "...", "email": "...", "phone": "...", "linkedin": "...",
  "summary": "2-3 sentence professional summary",
  "skills": ["skill1", ...],
  "experience": [{{"title": "...", "company": "...", "duration": "...", "bullets": ["...", ...]}}],
  "projects": [{{"name": "...", "description": "...", "technologies": ["..."], "bullets": ["..."]}}],
  "education": [{{"degree": "...", "institution": "...", "year": "...", "gpa": "..."}}],
  "certifications": ["..."],
  "preview_text": "2-3 sentence preview of key improvements"
}}

Return ONLY valid JSON.
"""


def rewrite_resume(
    resume_data: ResumeData,
    jd_analysis: JDAnalysis,
    version_type: str
) -> RewrittenResume:
    if version_type not in VERSION_CONFIGS:
        raise ValueError(f"Invalid version type: {version_type}")

    config = VERSION_CONFIGS[version_type]
    client = get_llm_client()

    resume_dict = {
        "name": resume_data.name,
        "email": resume_data.email,
        "phone": resume_data.phone,
        "linkedin": resume_data.linkedin,
        "summary": resume_data.summary,
        "skills": resume_data.skills,
        "experience": [exp.model_dump() for exp in resume_data.experience],
        "projects": [proj.model_dump() for proj in resume_data.projects],
        "education": [edu.model_dump() for edu in resume_data.education],
        "certifications": resume_data.certifications,
    }

    prompt = REWRITE_PROMPT.format(
        resume_json=json.dumps(resume_dict, indent=2),
        jd_title=jd_analysis.title,
        required_skills=", ".join(jd_analysis.required_skills),
        priority_keywords=", ".join(jd_analysis.priority_keywords),
        responsibilities="\n".join(f"  - {r}" for r in jd_analysis.responsibilities),
    )

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": config["system_prompt"]},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)

    return RewrittenResume(
        version_type=version_type,
        version_label=config["label"],
        name=data.get("name", resume_data.name),
        email=data.get("email", resume_data.email),
        phone=data.get("phone", resume_data.phone),
        linkedin=data.get("linkedin", resume_data.linkedin),
        summary=data.get("summary", ""),
        skills=data.get("skills", []),
        experience=data.get("experience", []),
        projects=data.get("projects", []),
        education=data.get("education", []),
        certifications=data.get("certifications", []),
        preview_text=data.get("preview_text", ""),
    )


def generate_all_versions(
    resume_data: ResumeData,
    jd_analysis: JDAnalysis
) -> list[RewrittenResume]:
    versions = []
    for version_type in VERSION_CONFIGS:
        versions.append(rewrite_resume(resume_data, jd_analysis, version_type))
    return versions
