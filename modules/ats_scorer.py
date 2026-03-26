"""
ATS Score Module
Calculates ATS (Applicant Tracking System) compatibility score for each resume version.
Scores based on keyword match, formatting simplicity, and section completeness.
"""
from pydantic import BaseModel, Field
from modules.jd_analyzer import JDAnalysis


# ── Data Models ──────────────────────────────────────────────────────────────

class ATSScoreBreakdown(BaseModel):
    """Detailed ATS score breakdown."""
    keyword_match_score: float = 0.0      # 0-100
    formatting_score: float = 0.0         # 0-100
    section_completeness_score: float = 0.0  # 0-100
    final_ats_score: int = 0              # 0-100
    details: dict = Field(default_factory=dict)


# ── ATS Scoring Functions ────────────────────────────────────────────────────

# Required sections for a complete resume
REQUIRED_SECTIONS = ["name", "skills", "experience", "education"]
OPTIONAL_SECTIONS = ["summary", "projects", "certifications", "email", "phone"]

# Formatting traits per version type
FORMATTING_SCORES = {
    "ats_optimized": 98,       # Simple, clean, no graphics — best for ATS
    "modern_professional": 82, # Some styling but still parseable
    "developer_focused": 85,   # Project-heavy but structured
}


def _calculate_keyword_match(resume_content: dict, jd_analysis: JDAnalysis) -> tuple[float, dict]:
    """
    Calculate what percentage of JD keywords are present in resume content.
    
    Returns:
        Tuple of (score, details_dict)
    """
    # Build resume text from content
    text_parts = []
    if resume_content.get("skills"):
        text_parts.append(" ".join(resume_content["skills"]))
    if resume_content.get("summary"):
        text_parts.append(resume_content["summary"])
    for exp in resume_content.get("experience", []):
        text_parts.append(exp.get("title", ""))
        text_parts.append(exp.get("company", ""))
        text_parts.extend(exp.get("bullets", []))
    for proj in resume_content.get("projects", []):
        text_parts.append(proj.get("name", ""))
        text_parts.append(proj.get("description", ""))
        text_parts.extend(proj.get("technologies", []))
        text_parts.extend(proj.get("bullets", []))

    full_text = " ".join(text_parts).lower()

    all_keywords = set()
    for kw in jd_analysis.keywords + jd_analysis.required_skills + jd_analysis.priority_keywords:
        all_keywords.add(kw.lower().strip())

    if not all_keywords:
        return 0.0, {"matched": 0, "total": 0, "missing": []}

    matched_keywords = []
    missing_keywords = []
    for keyword in all_keywords:
        if keyword in full_text:
            matched_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    score = (len(matched_keywords) / len(all_keywords)) * 100

    return score, {
        "matched": len(matched_keywords),
        "total": len(all_keywords),
        "matched_keywords": sorted(matched_keywords),
        "missing_keywords": sorted(missing_keywords)
    }


def _calculate_section_completeness(resume_content: dict) -> tuple[float, dict]:
    """
    Check if all required and optional sections are present and non-empty.
    
    Returns:
        Tuple of (score, details_dict)
    """
    present_required = []
    missing_required = []
    present_optional = []
    missing_optional = []

    for section in REQUIRED_SECTIONS:
        value = resume_content.get(section)
        if value and (isinstance(value, str) and value.strip()) or (isinstance(value, list) and len(value) > 0):
            present_required.append(section)
        else:
            missing_required.append(section)

    for section in OPTIONAL_SECTIONS:
        value = resume_content.get(section)
        if value and (isinstance(value, str) and value.strip()) or (isinstance(value, list) and len(value) > 0):
            present_optional.append(section)
        else:
            missing_optional.append(section)

    # Required sections are worth 70%, optional 30%
    required_score = (len(present_required) / len(REQUIRED_SECTIONS)) * 70 if REQUIRED_SECTIONS else 70
    optional_score = (len(present_optional) / len(OPTIONAL_SECTIONS)) * 30 if OPTIONAL_SECTIONS else 30
    total = required_score + optional_score

    return total, {
        "present_required": present_required,
        "missing_required": missing_required,
        "present_optional": present_optional,
        "missing_optional": missing_optional,
    }


def calculate_ats_score(
    resume_content: dict,
    jd_analysis: JDAnalysis,
    version_type: str
) -> ATSScoreBreakdown:
    """
    Calculate ATS compatibility score for a resume version.
    
    Args:
        resume_content: Dict with resume fields (name, skills, experience, etc.)
        jd_analysis: Analyzed JD data.
        version_type: One of 'ats_optimized', 'modern_professional', 'developer_focused'.
    
    Returns:
        ATSScoreBreakdown with individual and final scores.
    """
    # 1. Keyword match (50% weight)
    keyword_score, keyword_details = _calculate_keyword_match(resume_content, jd_analysis)

    # 2. Formatting simplicity (20% weight)
    formatting_score = FORMATTING_SCORES.get(version_type, 80)

    # 3. Section completeness (30% weight)
    completeness_score, completeness_details = _calculate_section_completeness(resume_content)

    # Weighted final score
    final_score = round(
        (keyword_score * 0.50) +
        (formatting_score * 0.20) +
        (completeness_score * 0.30)
    )
    final_score = max(0, min(100, final_score))

    return ATSScoreBreakdown(
        keyword_match_score=round(keyword_score, 1),
        formatting_score=float(formatting_score),
        section_completeness_score=round(completeness_score, 1),
        final_ats_score=final_score,
        details={
            "keyword_details": keyword_details,
            "completeness_details": completeness_details,
            "version_type": version_type,
        }
    )
