"""Librarian API routes."""

import base64
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from api.schemas.librarian import (
    LibrarianAnalyzeRequest,
    LibrarianQueryRequest,
    LibrarianSummaryResponse,
    LibrarianQueryResponse,
    FileManifestItem,
)
from src.librarian.service import LibrarianService
from src.models.librarian import LibrarianFile, LibrarianConfig

router = APIRouter()

# In-memory session storage (in production, use Redis with TTL)
librarian_sessions: dict[str, LibrarianService] = {}


@router.post("/librarian/analyze", response_model=LibrarianSummaryResponse)
async def analyze_documents(
    request: LibrarianAnalyzeRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> LibrarianSummaryResponse:
    """
    Analyze uploaded documents and generate a summary.
    Returns a session_id for subsequent queries.
    """
    # Convert uploaded files to LibrarianFile objects
    librarian_files = []
    for file_data in request.files:
        try:
            content = base64.b64decode(file_data.content_base64)
            librarian_files.append(LibrarianFile(
                filename=file_data.filename,
                content_type=file_data.content_type,
                content=content,
            ))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to decode file {file_data.filename}: {str(e)}"
            )
    
    # Create librarian config
    config = LibrarianConfig(
        model=request.model,
        temperature=0.1,  # Low temperature for factual extraction
    )
    
    # Create librarian service
    service = LibrarianService(
        api_key=x_api_key,
        config=config,
    )
    
    try:
        # Initialize with files and generate summary
        summary = await service.initialize(
            files=librarian_files,
            query=request.query,
        )
        
        # Generate session ID and store service
        session_id = str(uuid.uuid4())[:12]
        librarian_sessions[session_id] = service
        
        # Build response
        manifest = [
            FileManifestItem(
                filename=item.filename,
                file_type=item.file_type,
                description=item.description,
            )
            for item in summary.file_manifest
        ]
        
        return LibrarianSummaryResponse(
            session_id=session_id,
            summary=summary.summary,
            file_manifest=manifest,
            input_tokens=summary.input_tokens,
            output_tokens=summary.output_tokens,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze documents: {str(e)}"
        )


@router.post("/librarian/query", response_model=LibrarianQueryResponse)
async def query_librarian(
    request: LibrarianQueryRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> LibrarianQueryResponse:
    """
    Query the librarian about previously analyzed documents.
    Requires a valid session_id from a previous analyze call.
    """
    if request.session_id not in librarian_sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please analyze documents first."
        )
    
    service = librarian_sessions[request.session_id]
    
    try:
        # Query the librarian
        response = await service.query(request.question)
        
        return LibrarianQueryResponse(
            question=request.question,
            answer=response.answer,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query librarian: {str(e)}"
        )


@router.delete("/librarian/session/{session_id}")
async def close_session(session_id: str) -> dict:
    """Close a librarian session and free resources."""
    if session_id in librarian_sessions:
        del librarian_sessions[session_id]
        return {"status": "closed", "session_id": session_id}
    
    raise HTTPException(status_code=404, detail="Session not found")

