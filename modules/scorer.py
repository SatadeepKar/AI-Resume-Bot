"""
Resume Scorer Module
Calculates keyword match score, semantic similarity (TF-IDF based), and combined final score.
Uses TF-IDF + cosine similarity instead of embeddings (no external API needed).
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from modules.parser import ResumeData
from modules.jd_analyzer import JDAnalysis


# ── Keyword Match Score ──────────────────────────────────────────────────────

def calculate_keyword_score(resume_data: ResumeData, jd_analysis: JDAnalysis) -> float:
    resume_text_parts = [
        resume_data.raw_text.lower(),
        " ".join(resume_data.skills).lower(),
        resume_data.summary.lower(),
    ]
    resume_text = " ".join(resume_text_parts)

    all_keywords = set()
    for kw in jd_analysis.keywords + jd_analysis.required_skills + jd_analysis.priority_keywords:
        all_keywords.add(kw.lower().strip())

    if not all_keywords:
        return 0.0

    matched = sum(1 for kw in all_keywords if kw in resume_text)
    return matched / len(all_keywords)


def get_missing_keywords(resume_data: ResumeData, jd_analysis: JDAnalysis) -> list[str]:
    resume_text = resume_data.raw_text.lower()
    all_keywords = set()
    for kw in jd_analysis.keywords + jd_analysis.required_skills + jd_analysis.priority_keywords:
        all_keywords.add(kw.lower().strip())

    return sorted([kw for kw in all_keywords if kw not in resume_text])


# ── Semantic Similarity (TF-IDF based — no API needed) ──────────────────────

def calculate_semantic_score(resume_text: str, jd_text: str) -> float:
    """Calculate semantic similarity using TF-IDF + cosine similarity (free, local)."""
    if not resume_text.strip() or not jd_text.strip():
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
    similarity = sklearn_cosine(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    # Normalize to 0-1 range
    return max(0.0, min(1.0, float(similarity)))


# ── Combined Final Score ─────────────────────────────────────────────────────

def calculate_final_score(
    keyword_score: float,
    semantic_score: float,
    keyword_weight: float = 0.55,
    semantic_weight: float = 0.45
) -> int:
    combined = (keyword_score * keyword_weight) + (semantic_score * semantic_weight)
    return round(combined * 100)


def score_resume(resume_data: ResumeData, jd_analysis: JDAnalysis, jd_text: str) -> dict:
    keyword_score = calculate_keyword_score(resume_data, jd_analysis)
    semantic_score = calculate_semantic_score(resume_data.raw_text, jd_text)
    final_score = calculate_final_score(keyword_score, semantic_score)
    missing_keywords = get_missing_keywords(resume_data, jd_analysis)

    return {
        "keyword_score": round(keyword_score * 100),
        "semantic_score": round(semantic_score * 100),
        "final_score": final_score,
        "missing_keywords": missing_keywords
    }
