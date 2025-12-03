"""
Data models for the Librarian agent.

The Librarian is a special non-deliberating agent that:
1. Pre-conference: Analyzes uploaded files + query, generates a contextual summary
2. During deliberation: Answers agent queries about document contents
"""

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class FileType(str, Enum):
    """Supported file types for the Librarian."""
    
    PDF = "pdf"
    IMAGE = "image"  # jpg, png, gif, webp
    TEXT = "text"    # txt, md, csv
    UNKNOWN = "unknown"


class LibrarianConfig(BaseModel):
    """Configuration for the Librarian agent."""
    
    model: str = Field(
        default="google/gemini-3-pro-preview",
        description="Multimodal model for document analysis (must support PDF/images)"
    )
    max_queries_per_turn: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of queries an agent can make per turn"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Low temperature for precise, factual document extraction"
    )
    enabled: bool = Field(
        default=True,
        description="Whether the Librarian is active"
    )


class LibrarianFile(BaseModel):
    """A file provided to the Librarian for analysis."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Detected file type")
    content: bytes = Field(..., description="Raw file content as bytes")
    mime_type: str = Field(default="application/octet-stream", description="MIME type")
    size_bytes: int = Field(default=0, description="File size in bytes")
    
    @classmethod
    def from_upload(cls, filename: str, content: bytes, mime_type: str = "") -> "LibrarianFile":
        """
        Create a LibrarianFile from an uploaded file.
        
        Args:
            filename: Original filename
            content: Raw file bytes
            mime_type: Optional MIME type (will be inferred if not provided)
        
        Returns:
            LibrarianFile instance
        """
        # Infer file type from extension or mime type
        file_type = cls._infer_file_type(filename, mime_type)
        
        # Infer mime type if not provided
        if not mime_type:
            mime_type = cls._infer_mime_type(filename, file_type)
        
        return cls(
            filename=filename,
            file_type=file_type,
            content=content,
            mime_type=mime_type,
            size_bytes=len(content),
        )
    
    @staticmethod
    def _infer_file_type(filename: str, mime_type: str) -> FileType:
        """Infer FileType from filename extension or MIME type."""
        filename_lower = filename.lower()
        mime_lower = mime_type.lower()
        
        # Check by extension
        if filename_lower.endswith(".pdf"):
            return FileType.PDF
        elif any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
            return FileType.IMAGE
        elif any(filename_lower.endswith(ext) for ext in [".txt", ".md", ".csv", ".json"]):
            return FileType.TEXT
        
        # Check by MIME type
        if "pdf" in mime_lower:
            return FileType.PDF
        elif mime_lower.startswith("image/"):
            return FileType.IMAGE
        elif mime_lower.startswith("text/"):
            return FileType.TEXT
        
        return FileType.UNKNOWN
    
    @staticmethod
    def _infer_mime_type(filename: str, file_type: FileType) -> str:
        """Infer MIME type from filename and file type."""
        filename_lower = filename.lower()
        
        mime_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".json": "application/json",
        }
        
        for ext, mime in mime_map.items():
            if filename_lower.endswith(ext):
                return mime
        
        # Fallback based on file type
        type_mime_map = {
            FileType.PDF: "application/pdf",
            FileType.IMAGE: "image/png",
            FileType.TEXT: "text/plain",
        }
        return type_mime_map.get(file_type, "application/octet-stream")


class FileManifestEntry(BaseModel):
    """Entry in the file manifest describing an uploaded file."""
    
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Detected file type")
    size_bytes: int = Field(default=0, description="File size in bytes")
    description: str = Field(default="", description="Brief description of file contents")


class LibrarianSummary(BaseModel):
    """Summary generated by the Librarian after analyzing uploaded files."""
    
    summary: str = Field(..., description="Contextual summary of all uploaded documents")
    file_manifest: list[FileManifestEntry] = Field(
        default_factory=list,
        description="List of files that were analyzed"
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings extracted from the documents"
    )
    relevant_to_query: bool = Field(
        default=True,
        description="Whether the documents appear relevant to the query"
    )
    
    # Token usage for cost tracking
    input_tokens: int = Field(default=0, description="Input tokens consumed")
    output_tokens: int = Field(default=0, description="Output tokens generated")


class LibrarianQuery(BaseModel):
    """A query from an agent to the Librarian about document contents."""
    
    agent_id: str = Field(..., description="ID of the agent making the query")
    question: str = Field(..., description="The question about document contents")
    response: str = Field(default="", description="Librarian's response")
    round_number: int = Field(default=1, description="Conference round when query was made")
    
    # Token usage for cost tracking
    input_tokens: int = Field(default=0, description="Input tokens consumed")
    output_tokens: int = Field(default=0, description="Output tokens generated")


class LibrarianContext(BaseModel):
    """
    Complete Librarian context for a conference.
    
    Tracks the initial summary and all agent queries during deliberation.
    """
    
    config: LibrarianConfig = Field(
        default_factory=LibrarianConfig,
        description="Librarian configuration"
    )
    files: list[LibrarianFile] = Field(
        default_factory=list,
        description="Files provided for analysis"
    )
    summary: Optional[LibrarianSummary] = Field(
        default=None,
        description="Initial summary generated from files"
    )
    queries: list[LibrarianQuery] = Field(
        default_factory=list,
        description="All queries made during the conference"
    )
    
    # Track queries per agent per round for rate limiting
    _query_counts: dict[str, dict[int, int]] = {}
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def can_query(self, agent_id: str, round_number: int) -> bool:
        """
        Check if an agent can make another query this round.
        
        Args:
            agent_id: The agent's ID
            round_number: Current round number
        
        Returns:
            True if the agent has queries remaining
        """
        key = f"{agent_id}_{round_number}"
        count = sum(
            1 for q in self.queries 
            if q.agent_id == agent_id and q.round_number == round_number
        )
        return count < self.config.max_queries_per_turn
    
    def get_queries_remaining(self, agent_id: str, round_number: int) -> int:
        """Get number of queries remaining for an agent this round."""
        count = sum(
            1 for q in self.queries 
            if q.agent_id == agent_id and q.round_number == round_number
        )
        return max(0, self.config.max_queries_per_turn - count)
    
    def add_query(self, query: LibrarianQuery) -> None:
        """Add a query to the context."""
        self.queries.append(query)
    
    @property
    def total_input_tokens(self) -> int:
        """Total input tokens used by Librarian."""
        summary_tokens = self.summary.input_tokens if self.summary else 0
        query_tokens = sum(q.input_tokens for q in self.queries)
        return summary_tokens + query_tokens
    
    @property
    def total_output_tokens(self) -> int:
        """Total output tokens used by Librarian."""
        summary_tokens = self.summary.output_tokens if self.summary else 0
        query_tokens = sum(q.output_tokens for q in self.queries)
        return summary_tokens + query_tokens

