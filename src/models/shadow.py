"""
Data models for Shadow Mode (counterfactual evaluation).

Shadow Mode allows replaying past queries with alternative configurations
to learn which settings work best without requiring user feedback.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Preference(str, Enum):
    """Overall preference from judge comparison."""
    
    ORIGINAL = "original"
    ALTERNATIVE = "alternative"
    TIE = "tie"


class JudgeScores(BaseModel):
    """Multi-axis evaluation scores from judge model."""
    
    # Individual axis scores (0-10)
    accuracy: float = Field(..., ge=0, le=10, description="Factual accuracy")
    evidence: float = Field(..., ge=0, le=10, description="Evidence quality")
    calibration: float = Field(..., ge=0, le=10, description="Uncertainty calibration")
    actionability: float = Field(..., ge=0, le=10, description="Clear recommendation")
    safety: float = Field(..., ge=0, le=10, description="Risks acknowledged")
    
    # Overall preference
    overall_preference: Preference = Field(..., description="Which response is better")
    
    # Optional reasoning
    reasoning: Optional[str] = Field(default=None, description="Judge's explanation")
    
    @property
    def total_score(self) -> float:
        """Calculate weighted total score."""
        weights = {
            "accuracy": 0.25,
            "evidence": 0.20,
            "calibration": 0.15,
            "actionability": 0.20,
            "safety": 0.20,
        }
        return (
            self.accuracy * weights["accuracy"] +
            self.evidence * weights["evidence"] +
            self.calibration * weights["calibration"] +
            self.actionability * weights["actionability"] +
            self.safety * weights["safety"]
        )
    
    @property
    def is_better(self) -> bool:
        """Check if alternative is better than original."""
        return self.overall_preference == Preference.ALTERNATIVE


class ShadowResult(BaseModel):
    """Result from a shadow (counterfactual) conference run."""
    
    # Identifiers
    shadow_id: str = Field(..., description="Unique ID for this shadow run")
    original_conference_id: str = Field(..., description="ID of original conference")
    
    # Configuration used
    config_signature: str = Field(..., description="Signature of alternative config")
    
    # Results
    synthesis: str = Field(..., description="Synthesis from alternative config")
    scores: JudgeScores = Field(..., description="Judge evaluation scores")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    duration_ms: int = Field(default=0, description="Time taken for shadow run")
    
    # Cost tracking
    tokens_used: int = Field(default=0)
    estimated_cost: float = Field(default=0.0)


class ShadowBatch(BaseModel):
    """A batch of shadow runs for overnight processing."""
    
    batch_id: str = Field(..., description="Unique batch ID")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Configuration
    conference_ids: list[str] = Field(
        default_factory=list,
        description="Conference IDs to replay"
    )
    alternative_configs: list[str] = Field(
        default_factory=list,
        description="Config signatures to try"
    )
    
    # Status
    status: str = Field(default="pending", description="pending, running, completed, failed")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    results: list[ShadowResult] = Field(default_factory=list)
    
    # Summary stats
    total_runs: int = Field(default=0)
    completed_runs: int = Field(default=0)
    improvements_found: int = Field(default=0)
    
    def add_result(self, result: ShadowResult):
        """Add a result and update stats."""
        self.results.append(result)
        self.completed_runs += 1
        if result.scores.is_better:
            self.improvements_found += 1


class ShadowInsight(BaseModel):
    """Insight derived from shadow mode analysis."""
    
    insight_type: str = Field(
        ...,
        description="Type: config_better, model_better, rounds_better, etc."
    )
    description: str = Field(..., description="Human-readable insight")
    
    # Evidence
    sample_size: int = Field(default=0)
    confidence: str = Field(default="LOW", description="LOW, MEDIUM, HIGH")
    
    # Recommendations
    recommendation: Optional[str] = Field(
        default=None,
        description="Suggested action based on insight"
    )
    
    # Affected queries
    query_types: list[str] = Field(
        default_factory=list,
        description="Query types this insight applies to"
    )


class ShadowSummary(BaseModel):
    """Summary of shadow mode findings."""
    
    period_start: datetime
    period_end: datetime
    
    # Volume
    total_shadow_runs: int = Field(default=0)
    conferences_replayed: int = Field(default=0)
    configs_tested: int = Field(default=0)
    
    # Findings
    improvements_found: int = Field(default=0)
    improvement_rate: float = Field(default=0.0)
    
    # Insights
    insights: list[ShadowInsight] = Field(default_factory=list)
    
    # Best performing
    best_config_signature: Optional[str] = None
    best_config_avg_score: Optional[float] = None
    
    # Cost
    total_tokens: int = Field(default=0)
    total_cost: float = Field(default=0.0)

