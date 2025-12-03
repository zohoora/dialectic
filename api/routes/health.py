"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "ai-case-conference"}


@router.get("/")
async def root():
    """API root."""
    return {
        "name": "AI Case Conference API",
        "version": "1.0.0",
        "docs": "/docs",
    }

