"""
Shared Protocol definitions for type hints across the codebase.

These protocols define the interfaces expected from external dependencies
like LLM clients, allowing for dependency injection and testing.
"""

from typing import Optional, Protocol

from src.models.conference import LLMResponse


class LLMClientProtocol(Protocol):
    """
    Protocol defining the interface for LLM clients.
    
    This protocol is used throughout the codebase to type-hint
    LLM client dependencies without coupling to a specific implementation.
    """
    
    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Complete a chat conversation with the LLM.
        
        Args:
            model: Model identifier (e.g., "openai/gpt-4o")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0-1)
            max_tokens: Optional maximum tokens to generate
            
        Returns:
            LLMResponse with content and token usage
        """
        ...
    
    async def complete_multimodal(
        self,
        model: str,
        messages: list[dict],
        files: Optional[list[tuple[bytes, str]]],
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Complete a multimodal conversation (with files/images).
        
        Args:
            model: Model identifier
            messages: List of message dicts
            files: Optional list of (content_bytes, mime_type) tuples
            temperature: Sampling temperature
            max_tokens: Optional maximum tokens
            
        Returns:
            LLMResponse with content and token usage
        """
        ...
    
    def get_session_usage(self) -> dict:
        """
        Get token usage statistics for the current session.
        
        Returns:
            Dict with usage statistics
        """
        ...
    
    def reset_session(self) -> None:
        """Reset session tracking for a new conversation."""
        ...


class LibrarianServiceProtocol(Protocol):
    """Protocol for librarian service to allow dependency injection."""
    
    async def process_agent_queries(
        self,
        agent_id: str,
        response_text: str,
        round_number: int,
    ) -> list:
        """
        Process queries from an agent's response.
        
        Args:
            agent_id: ID of the agent making the query
            response_text: The agent's response text
            round_number: Current round number
            
        Returns:
            List of query results
        """
        ...
    
    @staticmethod
    def format_query_answers(queries: list) -> str:
        """
        Format query answers for injection into prompts.
        
        Args:
            queries: List of query results
            
        Returns:
            Formatted string for prompt injection
        """
        ...

