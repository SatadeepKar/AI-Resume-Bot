"""
FastAPI API Routes
Handles resume upload, scoring, version generation, and file downloads.
Split into two phases: fast scoring first, then on-demand version generation.
"""
import os
import uuid
import traceback
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from config import settings
from modules.parser import parse_resume, ResumeData
from modules.jd_analyzer import analyze_jd, JDAnalysis
from modules.scorer import score_resume
from modules.ats_scorer import calculate_ats_score
from modules.ai_rewriter import rewrite_resume, RewrittenResume
from modules.template_engine import render_resume
from modules.pdf_generator import generate_pdf, generate_docx


router = APIRouter()

# ── In-Memory Session Storage ────────────────────────────────────────────────
sessions: dict[str, dict] = {}


# ── Helper Functions ─────────────────────────────────────────────────────────

async def save_upload_file(upload_file: UploadFile, session_id: str) -> str:
    """Save an uploaded file to disk and return the file path."""
    session_dir = os.path.join(settings.UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    file_path = os.path.join(session_dir, upload_file.filename)
    content = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def version_to_dict(version: RewrittenResume) -> dict:
    """Convert RewrittenResume to a dict suitable for rendering."""
    return {
        "name": version.name,
        "email": version.email,
        "phone": version.phone,
        "linkedin": version.linkedin,
        "summary": version.summary,
        "skills": version.skills,
        "experience": version.experience,
        "projects": version.projects,
        "education": version.education,
        "certifications": version.certifications,
    }


# ── Phase 1: Fast Score (parse + analyze + score only) ───────────────────────

@router.post("/score")
async def score_resume_endpoint(
    resume: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    jd_text: str = Form(..., description="Job description text"),
):
    """
    FAST — Upload resume + JD, get original score and suggestions.
    Does NOT generate rewritten versions (that's Phase 2).
    """
    filename = resume.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".docx") or filename.endswith(".doc")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a PDF or DOCX file.")

    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is required.")

    session_id = str(uuid.uuid4())

    try:
        # 1. Save uploaded file
        file_path = await save_upload_file(resume, session_id)

        # 2. Parse resume
        resume_data = parse_resume(file_path)

        # 3. Analyze JD
        jd_analysis = analyze_jd(jd_text)

        # 4. Score original resume
        original_score = score_resume(resume_data, jd_analysis, jd_text)

        # 5. Calculate original ATS score
        resume_dict = {
            "name": resume_data.name,
            "skills": resume_data.skills,
            "experience": [exp.model_dump() for exp in resume_data.experience],
            "projects": [proj.model_dump() for proj in resume_data.projects],
            "education": [edu.model_dump() for edu in resume_data.education],
            "summary": resume_data.summary,
            "email": resume_data.email,
            "phone": resume_data.phone,
            "certifications": resume_data.certifications,
        }
        original_ats = calculate_ats_score(resume_dict, jd_analysis, "ats_optimized")

        # 6. Store session for Phase 2
        sessions[session_id] = {
            "resume_data": resume_data,
            "jd_analysis": jd_analysis,
            "jd_text": jd_text,
            "original_score": original_score,
            "versions": {},
        }

        return {
            "session_id": session_id,
            "original_score": original_score,
            "original_ats_score": original_ats.final_ats_score,
            "ats_breakdown": {
                "keyword_match": original_ats.keyword_match_score,
                "formatting": original_ats.formatting_score,
                "section_completeness": original_ats.section_completeness_score,
            },
            "missing_keywords": original_score.get("missing_keywords", []),
            "parsed_skills": resume_data.skills,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


# ── Phase 2: Generate a single version on-demand ────────────────────────────

@router.post("/rewrite/{session_id}/{version_type}")
async def rewrite_version(session_id: str, version_type: str):
    """
    Generate ONE rewritten version on-demand. Much faster than generating all 3 at once.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired. Please re-analyze.")

    valid_types = ["ats_optimized", "modern_professional", "developer_focused"]
    if version_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid version type. Choose from: {valid_types}")

    session = sessions[session_id]

    # Check if already generated
    if version_type in session["versions"]:
        version = session["versions"][version_type]
        v_dict = version_to_dict(version)
        ats = calculate_ats_score(v_dict, session["jd_analysis"], version_type)
        return {
            "version_type": version_type,
            "version_label": version.version_label,
            "ats_score": ats.final_ats_score,
            "preview_text": version.preview_text,
            "cached": True,
        }

    try:
        # Generate just this one version
        version = rewrite_resume(session["resume_data"], session["jd_analysis"], version_type)

        # Calculate ATS score
        v_dict = version_to_dict(version)
        ats = calculate_ats_score(v_dict, session["jd_analysis"], version_type)

        # Cache it
        session["versions"][version_type] = version

        return {
            "version_type": version_type,
            "version_label": version.version_label,
            "ats_score": ats.final_ats_score,
            "ats_breakdown": {
                "keyword_match": ats.keyword_match_score,
                "formatting": ats.formatting_score,
                "section_completeness": ats.section_completeness_score,
            },
            "preview_text": version.preview_text,
            "cached": False,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Rewrite error: {str(e)}")


# ── Phase 3: Generate downloadable file ──────────────────────────────────────

@router.post("/generate/{session_id}/{version_type}")
async def generate_version(session_id: str, version_type: str, format: str = "pdf"):
    """Generate a downloadable PDF/DOCX for a selected resume version."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    session = sessions[session_id]
    versions = session["versions"]

    if version_type not in versions:
        raise HTTPException(status_code=400, detail=f"Version '{version_type}' not generated yet. Call /rewrite first.")

    version = versions[version_type]
    v_dict = version_to_dict(version)

    try:
        output_dir = os.path.join(settings.OUTPUT_DIR, session_id)
        os.makedirs(output_dir, exist_ok=True)

        if format == "pdf":
            html_content = render_resume(v_dict, version_type)
            filename = f"{version.name.replace(' ', '_')}_{version_type}.pdf"
            output_path = os.path.join(output_dir, filename)
            generate_pdf(html_content, output_path)
        elif format == "docx":
            filename = f"{version.name.replace(' ', '_')}_{version_type}.docx"
            output_path = os.path.join(output_dir, filename)
            generate_docx(v_dict, output_path)
        else:
            raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'docx'.")

        download_url = f"{settings.API_BASE_URL}/api/download/{session_id}/{filename}"

        return {
            "status": "success",
            "version_type": version_type,
            "format": format,
            "filename": filename,
            "download_url": download_url,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")


@router.get("/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    """Download a generated resume file."""
    file_path = os.path.join(settings.OUTPUT_DIR, session_id, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    media_type = "application/pdf" if filename.endswith(".pdf") else \
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(path=file_path, filename=filename, media_type=media_type)
