"""Librarian API schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class FileData(BaseModel):
    """Uploaded file data."""
    filename: str
    content_type: str
    content_base64: str  # Base64 encoded file content


class LibrarianAnalyzeRequest(BaseModel):
    """Request to analyze documents."""
    files: list[FileData] = Field(..., min_length=1)
    query: str = Field(..., description="The clinical question for context")
    model: str = Field(default="google/gemini-3-pro-preview")


class LibrarianQueryRequest(BaseModel):
    """Request to query the librarian about documents."""
    session_id: str = Field(..., description="Session ID from analyze response")
    question: str = Field(..., description="Question about the documents")


class FileManifestItem(BaseModel):
    """Single file in manifest."""
    filename: str
    file_type: str
    description: str


class LibrarianSummaryResponse(BaseModel):
    """Response from document analysis."""
    session_id: str
    summary: str
    file_manifest: list[FileManifestItem]
    input_tokens: int
    output_tokens: int


class LibrarianQueryResponse(BaseModel):
    """Response to a librarian query."""
    question: str
    answer: str
    input_tokens: int
    output_tokens: int

