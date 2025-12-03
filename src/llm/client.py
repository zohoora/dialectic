"""
OpenRouter LLM Client.

Provides a unified interface for calling LLMs via OpenRouter's API,
which is compatible with the OpenAI API format.
"""

import base64
import os
from typing import Optional, Union

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.conference import LLMResponse


def encode_file_for_message(content: bytes, mime_type: str) -> dict:
    """
    Encode file content as a base64 data URL for multimodal messages.
    
    Args:
        content: Raw file bytes
        mime_type: MIME type of the file (e.g., 'image/png', 'application/pdf')
    
    Returns:
        Dict with type and data URL for use in message content
    """
    b64_content = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_content}"
    
    # For PDFs, OpenRouter/Gemini uses a different format
    if mime_type == "application/pdf":
        return {
            "type": "file",
            "file": {
                "filename": "document.pdf",
                "file_data": data_url,
            }
        }
    else:
        # Images use the standard format
        return {
            "type": "image_url",
            "image_url": {"url": data_url}
        }


def build_multimodal_message(
    role: str,
    text: str,
    files: Optional[list[tuple[bytes, str]]] = None,
) -> dict:
    """
    Build a message dict with text and optional file attachments.
    
    Args:
        role: Message role ('user', 'assistant', 'system')
        text: Text content of the message
        files: Optional list of (content_bytes, mime_type) tuples
    
    Returns:
        Message dict compatible with OpenAI/OpenRouter API
    """
    if not files:
        return {"role": role, "content": text}
    
    # Build multimodal content array
    content = [{"type": "text", "text": text}]
    
    for file_content, mime_type in files:
        content.append(encode_file_for_message(file_content, mime_type))
    
    return {"role": role, "content": content}


class LLMClient:
    """
    Async client for OpenRouter API.
    
    Uses the OpenAI SDK with OpenRouter's base URL for compatibility.
    """
    
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        site_url: Optional[str] = None,
        site_name: Optional[str] = None,
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: OpenRouter API key. If not provided, reads from OPENROUTER_API_KEY env var.
            site_url: Optional site URL for OpenRouter attribution.
            site_name: Optional site name for OpenRouter attribution.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.site_url = site_url or os.getenv("OPENROUTER_SITE_URL", "http://localhost:8501")
        self.site_name = site_name or os.getenv("OPENROUTER_SITE_NAME", "AI Case Conference")
        
        # Initialize OpenAI client with OpenRouter base URL
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": self.site_url,
                "X-Title": self.site_name,
            },
        )
        
        # Track costs for this session
        self._session_costs: list[dict] = []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a completion from the specified model.
        
        Args:
            model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
            messages: List of message dicts with "role" and "content" keys
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate (optional)
        
        Returns:
            LLMResponse with content and token usage
        """
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = await self.client.chat.completions.create(**kwargs)
        
        # Extract response data
        content = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason or "stop"
        
        # Extract token usage
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        
        # Log for cost tracking
        self._session_costs.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
        )
    
    def get_session_usage(self) -> dict:
        """
        Get total token usage for this session.
        
        Returns:
            Dict with total input/output tokens by model
        """
        usage_by_model: dict[str, dict] = {}
        
        for call in self._session_costs:
            model = call["model"]
            if model not in usage_by_model:
                usage_by_model[model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "calls": 0,
                }
            usage_by_model[model]["input_tokens"] += call["input_tokens"]
            usage_by_model[model]["output_tokens"] += call["output_tokens"]
            usage_by_model[model]["calls"] += 1
        
        return usage_by_model
    
    def reset_session(self):
        """Reset session cost tracking."""
        self._session_costs = []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def complete_multimodal(
        self,
        model: str,
        messages: list[dict],
        files: Optional[list[tuple[bytes, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a completion with multimodal support (images, PDFs).
        
        Args:
            model: Model identifier (must support multimodal, e.g., "google/gemini-2.0-flash-001")
            messages: List of message dicts (last user message will have files attached)
            files: List of (content_bytes, mime_type) tuples to attach
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate (optional)
        
        Returns:
            LLMResponse with content and token usage
        """
        # If files provided, rebuild the last user message with attachments
        if files:
            processed_messages = []
            for i, msg in enumerate(messages):
                if i == len(messages) - 1 and msg.get("role") == "user":
                    # Attach files to the last user message
                    text = msg.get("content", "")
                    processed_messages.append(
                        build_multimodal_message("user", text, files)
                    )
                else:
                    processed_messages.append(msg)
            messages = processed_messages
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = await self.client.chat.completions.create(**kwargs)
        
        # Extract response data
        content = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason or "stop"
        
        # Extract token usage
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        
        # Log for cost tracking
        self._session_costs.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
        )


class MockLLMClient:
    """
    Mock LLM client for testing.
    
    Returns predefined responses without making actual API calls.
    """
    
    def __init__(self, responses: Optional[dict[str, str]] = None):
        """
        Initialize mock client.
        
        Args:
            responses: Optional dict mapping model names to response content.
                      If not provided, returns a generic response.
        """
        self.responses = responses or {}
        self.calls: list[dict] = []
        self._session_costs: list[dict] = []
    
    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Return a mock response."""
        # Record the call for verification
        self.calls.append({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        
        # Get response content
        if model in self.responses:
            content = self.responses[model]
        else:
            content = f"Mock response from {model}"
        
        # Simulate token usage
        input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        output_tokens = len(content) // 4
        
        self._session_costs.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason="stop",
        )
    
    def get_session_usage(self) -> dict:
        """Get mock session usage."""
        usage_by_model: dict[str, dict] = {}
        for call in self._session_costs:
            model = call["model"]
            if model not in usage_by_model:
                usage_by_model[model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "calls": 0,
                }
            usage_by_model[model]["input_tokens"] += call["input_tokens"]
            usage_by_model[model]["output_tokens"] += call["output_tokens"]
            usage_by_model[model]["calls"] += 1
        return usage_by_model
    
    def reset_session(self):
        """Reset mock session."""
        self._session_costs = []
        self.calls = []
    
    async def complete_multimodal(
        self,
        model: str,
        messages: list[dict],
        files: Optional[list[tuple[bytes, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Return a mock multimodal response."""
        # Just delegate to the regular complete method
        return await self.complete(model, messages, temperature, max_tokens)

