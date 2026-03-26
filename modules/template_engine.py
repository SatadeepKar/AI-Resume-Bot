"""
Template Engine Module
Renders resume data into HTML using Jinja2 templates.
"""
import os
from jinja2 import Environment, FileSystemLoader

from config import settings


# ── Template Mapping ─────────────────────────────────────────────────────────

TEMPLATE_MAP = {
    "ats_optimized": "ats_friendly.html",
    "modern_professional": "modern_professional.html",
    "developer_focused": "developer_focused.html",
}


def get_template_env() -> Environment:
    """Create Jinja2 environment pointing to the templates directory."""
    return Environment(
        loader=FileSystemLoader(settings.TEMPLATE_DIR),
        autoescape=True
    )


def render_resume(resume_data: dict, template_name: str) -> str:
    """
    Render resume data into HTML using a specific template.
    
    Args:
        resume_data: Dict containing resume fields (name, skills, experience, etc.)
        template_name: Template key — one of 'ats_friendly', 'modern_professional', 'developer_focused'
                       OR a version type key like 'ats_optimized'.
    
    Returns:
        Rendered HTML string.
    """
    # Resolve template name
    template_file = TEMPLATE_MAP.get(template_name, template_name)
    if not template_file.endswith(".html"):
        template_file += ".html"

    env = get_template_env()

    template_path = os.path.join(settings.TEMPLATE_DIR, template_file)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_file}")

    template = env.get_template(template_file)
    html = template.render(**resume_data)
    return html
