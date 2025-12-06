"""
AI Case Conference System - Patient Context

Patient information models for context-aware reasoning.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PatientContext(BaseModel):
    """Patient information provided with the query."""

    model_config = ConfigDict(use_enum_values=True)

    age: Optional[int] = Field(default=None, ge=0, le=150)
    sex: Optional[Literal["male", "female", "other"]] = None
    comorbidities: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    failed_treatments: list[str] = Field(default_factory=list)
    relevant_history: Optional[str] = None
    constraints: list[str] = Field(
        default_factory=list,
        description="e.g., needle phobia, cost sensitive, rural location",
    )

