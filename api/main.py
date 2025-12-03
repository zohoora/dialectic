"""
FastAPI backend for AI Case Conference.

Provides REST API and Server-Sent Events (SSE) for real-time streaming
of agent responses during deliberation.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.routes import conference, librarian, health

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    print("🚀 AI Case Conference API starting...")
    yield
    # Shutdown
    print("👋 API shutting down...")


app = FastAPI(
    title="AI Case Conference API",
    description="Multi-agent clinical deliberation system with real-time streaming",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(conference.router, prefix="/api", tags=["Conference"])
app.include_router(librarian.router, prefix="/api", tags=["Librarian"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

