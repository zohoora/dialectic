"""
Data models for the Feedback & Learning system.

Captures user feedback signals at multiple timescales to enable
configuration optimization and library curation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Types of feedback signals."""
    
    # Immediate signals
    REGENERATED = "regenerated"  # User regenerated (negative)
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    COPIED = "copied"  # User copied/exported
    TIME_ON_PAGE = "time_on_page"
    
    # Post-conference explicit
    ACTED_ON_YES = "acted_on_yes"
    ACTED_ON_MODIFIED = "acted_on_modified"
    ACTED_ON_NO = "acted_on_no"
    DISSENT_USEFUL = "dissent_useful"
    
    # Delayed outcome (2 weeks later)
    DELAYED_WORKED = "delayed_worked"
    DELAYED_PARTIAL = "delayed_partial"
    DELAYED_DIDNT_HELP = "delayed_didnt_help"
    DELAYED_ADVERSE = "delayed_adverse"
    DELAYED_DIDNT_TRY = "delayed_didnt_try"
    DELAYED_ONGOING = "delayed_ongoing"


# Signal weights for outcome computation
SIGNAL_WEIGHTS = {
    SignalType.REGENERATED: -0.3,
    SignalType.THUMBS_UP: 0.5,
    SignalType.THUMBS_DOWN: -0.5,
    SignalType.COPIED: 0.2,
    SignalType.TIME_ON_PAGE: 0.1,  # Small positive for engagement
    SignalType.ACTED_ON_YES: 0.7,
    SignalType.ACTED_ON_MODIFIED: 0.4,
    SignalType.ACTED_ON_NO: -0.2,
    SignalType.DISSENT_USEFUL: 0.3,
    SignalType.DELAYED_WORKED: 1.0,
    SignalType.DELAYED_PARTIAL: 0.5,
    SignalType.DELAYED_DIDNT_HELP: -0.5,
    SignalType.DELAYED_ADVERSE: -1.0,
    SignalType.DELAYED_DIDNT_TRY: 0.0,
    SignalType.DELAYED_ONGOING: 0.3,
}


class FeedbackSignal(BaseModel):
    """A single feedback signal from user interaction."""
    
    signal_type: SignalType = Field(..., description="Type of feedback signal")
    value: float = Field(
        default=1.0,
        description="Signal value (usually 1.0, but can vary for time_on_page)"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def weight(self) -> float:
        """Get the weight for this signal type."""
        return SIGNAL_WEIGHTS.get(self.signal_type, 0.0)


class ImmediateFeedback(BaseModel):
    """Feedback collected immediately after conference."""
    
    useful: Optional[str] = Field(
        default=None,
        description="yes, partially, no"
    )
    will_act: Optional[str] = Field(
        default=None,
        description="yes, modified, no"
    )
    dissent_useful: Optional[bool] = Field(
        default=None,
        description="Whether the dissent was useful"
    )
    
    def to_signals(self) -> list[FeedbackSignal]:
        """Convert to FeedbackSignal list."""
        signals = []
        
        if self.useful == "yes":
            signals.append(FeedbackSignal(signal_type=SignalType.THUMBS_UP))
        elif self.useful == "no":
            signals.append(FeedbackSignal(signal_type=SignalType.THUMBS_DOWN))
        
        if self.will_act == "yes":
            signals.append(FeedbackSignal(signal_type=SignalType.ACTED_ON_YES))
        elif self.will_act == "modified":
            signals.append(FeedbackSignal(signal_type=SignalType.ACTED_ON_MODIFIED))
        elif self.will_act == "no":
            signals.append(FeedbackSignal(signal_type=SignalType.ACTED_ON_NO))
        
        if self.dissent_useful:
            signals.append(FeedbackSignal(signal_type=SignalType.DISSENT_USEFUL))
        
        return signals


class DelayedFeedback(BaseModel):
    """Feedback collected ~2 weeks after conference."""
    
    outcome: Optional[str] = Field(
        default=None,
        description="worked, partial, didnt_help, adverse, didnt_try, ongoing"
    )
    details: Optional[str] = Field(
        default=None,
        description="Optional free-text details"
    )
    
    def to_signals(self) -> list[FeedbackSignal]:
        """Convert to FeedbackSignal list."""
        signals = []
        
        outcome_map = {
            "worked": SignalType.DELAYED_WORKED,
            "partial": SignalType.DELAYED_PARTIAL,
            "didnt_help": SignalType.DELAYED_DIDNT_HELP,
            "adverse": SignalType.DELAYED_ADVERSE,
            "didnt_try": SignalType.DELAYED_DIDNT_TRY,
            "ongoing": SignalType.DELAYED_ONGOING,
        }
        
        if self.outcome and self.outcome in outcome_map:
            signals.append(FeedbackSignal(signal_type=outcome_map[self.outcome]))
        
        return signals


class ConferenceFeedback(BaseModel):
    """Complete feedback record for a conference."""
    
    conference_id: str = Field(..., description="ID of the conference")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # All signals collected
    signals: list[FeedbackSignal] = Field(default_factory=list)
    
    # Structured feedback
    immediate: Optional[ImmediateFeedback] = None
    delayed: Optional[DelayedFeedback] = None
    
    # Computed outcome
    outcome_score: Optional[float] = Field(
        default=None,
        description="Computed outcome score (0-1)"
    )
    
    def add_signal(self, signal: FeedbackSignal):
        """Add a feedback signal."""
        self.signals.append(signal)
        self._recompute_outcome()
    
    def add_immediate(self, feedback: ImmediateFeedback):
        """Add immediate feedback."""
        self.immediate = feedback
        self.signals.extend(feedback.to_signals())
        self._recompute_outcome()
    
    def add_delayed(self, feedback: DelayedFeedback):
        """Add delayed feedback."""
        self.delayed = feedback
        self.signals.extend(feedback.to_signals())
        self._recompute_outcome()
    
    def _recompute_outcome(self):
        """Recompute outcome score from signals."""
        if not self.signals:
            self.outcome_score = None
            return
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for signal in self.signals:
            weight = signal.weight
            weighted_sum += weight * signal.value
            total_weight += abs(weight)
        
        if total_weight == 0:
            self.outcome_score = 0.5  # Neutral
        else:
            # Normalize to [0, 1]
            raw = weighted_sum / total_weight
            self.outcome_score = (raw + 1) / 2


class QueryClassification(BaseModel):
    """Classification of a query for optimization."""
    
    query_type: str = Field(
        default="general",
        description="Type: diagnostic, treatment, procedural, general"
    )
    domain: str = Field(
        default="general",
        description="Medical domain"
    )
    complexity: str = Field(
        default="medium",
        description="low, medium, high"
    )
    
    def signature(self) -> str:
        """Create a hashable signature for this classification."""
        return f"{self.query_type}:{self.domain}:{self.complexity}"


class ConfigSignature(BaseModel):
    """Signature of a conference configuration for tracking."""
    
    topology: str = Field(default="free_discussion")
    num_rounds: int = Field(default=2)
    num_agents: int = Field(default=3)
    arbitrator_model: str = Field(default="")
    agent_models: list[str] = Field(default_factory=list)
    grounding_enabled: bool = Field(default=True)
    fragility_enabled: bool = Field(default=True)
    
    def signature(self) -> str:
        """Create a hashable signature."""
        return (
            f"{self.topology}:{self.num_rounds}:{self.num_agents}:"
            f"{self.arbitrator_model}:{','.join(sorted(self.agent_models))}:"
            f"{self.grounding_enabled}:{self.fragility_enabled}"
        )


class ComponentEffect(BaseModel):
    """Effect of a configuration component on outcomes."""
    
    component_type: str = Field(..., description="Type of component")
    component_value: str = Field(..., description="Value of the component")
    effect_size: Optional[float] = Field(
        default=None,
        description="Mean outcome for this component"
    )
    confidence: str = Field(
        default="LOW",
        description="LOW, MEDIUM, HIGH based on sample size"
    )
    sample_size: int = Field(default=0)
    std_dev: Optional[float] = Field(default=None)


class OptimizerState(BaseModel):
    """Serializable state of the configuration optimizer."""
    
    # Thompson Sampling posteriors: key -> {alpha, beta}
    posteriors: dict[str, dict[str, float]] = Field(default_factory=dict)
    
    # Component attribution data
    component_effects: dict[str, dict[str, float]] = Field(default_factory=dict)
    
    # Metadata
    total_observations: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.now)

