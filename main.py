"""
FastAPI Application Entry Point
Main server for the AI Resume Bot API.
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from api.routes import router


# ── App Initialization ───────────────────────────────────────────────────────

app = FastAPI(
    title="AI Resume Bot API",
    description="Analyze, score, and generate optimized resume versions tailored to job descriptions.",
    version="1.0.0",
)

# CORS for frontend/bot access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated files as static
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

# Include API router
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "AI Resume Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ── Run Server ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
