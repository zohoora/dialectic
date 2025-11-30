"""
Configuration Optimizer using Thompson Sampling.

Learns which conference configurations produce the best outcomes
for different query types using a contextual bandit approach.
"""

import json
import logging
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.conference import ConferenceConfig
from src.models.feedback import (
    ComponentEffect,
    ConfigSignature,
    ConferenceFeedback,
    OptimizerState,
    QueryClassification,
)


logger = logging.getLogger(__name__)


# Knowledge type half-lives in months
HALF_LIVES_MONTHS = {
    "model_performance": 2,      # Models update frequently
    "topology_effectiveness": 6,  # More stable
    "domain_heuristic": 18,       # Medical knowledge changes slowly
    "user_preference": 12,        # People are fairly consistent
    "default": 6,
}


def get_decayed_weight(
    observation_date: datetime,
    knowledge_type: str = "default",
) -> float:
    """
    Calculate time-weighted decay for an observation.
    
    Args:
        observation_date: When the observation was made
        knowledge_type: Type of knowledge (affects decay rate)
        
    Returns:
        Weight between 0 and 1
    """
    months_elapsed = (datetime.now() - observation_date).days / 30
    half_life = HALF_LIVES_MONTHS.get(knowledge_type, HALF_LIVES_MONTHS["default"])
    return 0.5 ** (months_elapsed / half_life)


class ConfigurationOptimizer:
    """
    Contextual bandit for selecting optimal conference configurations.
    
    Uses Thompson Sampling with Beta distributions to balance
    exploration and exploitation.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the optimizer.
        
        Args:
            storage_path: Path for persisting optimizer state
        """
        self.storage_path = storage_path
        
        # Thompson Sampling: Beta distributions for (query_type, config) pairs
        # Format: {key: {"alpha": float, "beta": float}}
        self.posteriors: dict[str, dict[str, float]] = defaultdict(
            lambda: {"alpha": 1.0, "beta": 1.0}
        )
        
        # Component attribution: {key: {"sum": float, "count": int, "sum_sq": float}}
        self.component_effects: dict[str, dict[str, float]] = defaultdict(
            lambda: {"sum": 0.0, "count": 0, "sum_sq": 0.0}
        )
        
        # Observation history for decay
        self.observations: list[dict] = []
        
        # Load from storage if exists
        if storage_path and storage_path.exists():
            self._load_from_storage()
    
    def select_configuration(
        self,
        query_class: QueryClassification,
        available_configs: list[ConferenceConfig],
    ) -> ConferenceConfig:
        """
        Select the best configuration using Thompson Sampling.
        
        Args:
            query_class: Classification of the query
            available_configs: Available configurations to choose from
            
        Returns:
            Selected configuration
        """
        if not available_configs:
            raise ValueError("No configurations available")
        
        if len(available_configs) == 1:
            return available_configs[0]
        
        # Sample from posterior for each config
        samples = {}
        
        for config in available_configs:
            sig = self._config_signature(config)
            key = f"{query_class.signature()}:{sig}"
            
            # Get or create Beta distribution parameters
            if key in self.posteriors:
                alpha = self.posteriors[key]["alpha"]
                beta = self.posteriors[key]["beta"]
            else:
                alpha, beta = 1.0, 1.0
            
            # Sample from Beta distribution
            samples[id(config)] = random.betavariate(alpha, beta)
        
        # Select config with highest sample
        best_config_id = max(samples, key=samples.get)
        
        for config in available_configs:
            if id(config) == best_config_id:
                logger.debug(
                    f"Selected config with signature {self._config_signature(config)} "
                    f"(sample: {samples[best_config_id]:.3f})"
                )
                return config
        
        # Fallback (shouldn't happen)
        return available_configs[0]
    
    def update(
        self,
        query_class: QueryClassification,
        config: ConferenceConfig,
        outcome_score: float,
    ):
        """
        Update posteriors based on outcome.
        
        Args:
            query_class: Classification of the query
            config: Configuration that was used
            outcome_score: Outcome score (0-1)
        """
        sig = self._config_signature(config)
        key = f"{query_class.signature()}:{sig}"
        
        # Ensure key exists
        if key not in self.posteriors:
            self.posteriors[key] = {"alpha": 1.0, "beta": 1.0}
        
        # Update Beta distribution
        # Treat outcome_score as probability of "success"
        if random.random() < outcome_score:
            self.posteriors[key]["alpha"] += 1
        else:
            self.posteriors[key]["beta"] += 1
        
        # Update component attribution
        self._update_components(query_class, config, outcome_score)
        
        # Record observation for decay
        self.observations.append({
            "query_class": query_class.signature(),
            "config": sig,
            "outcome": outcome_score,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Save state
        self._save_to_storage()
        
        logger.info(
            f"Updated optimizer for {query_class.query_type}: "
            f"outcome={outcome_score:.2f}, config={sig[:30]}..."
        )
    
    def _update_components(
        self,
        query_class: QueryClassification,
        config: ConferenceConfig,
        outcome: float,
    ):
        """Update component-level attribution."""
        # Extract components from config
        components = [
            ("topology", getattr(config, "topology", "free_discussion")),
            ("num_rounds", str(config.num_rounds)),
            ("arbitrator_model", config.arbitrator.model),
        ]
        
        for agent in config.agents:
            # Handle role as either string or enum
            role = agent.role.value if hasattr(agent.role, 'value') else str(agent.role)
            components.append(("agent_role", role))
            components.append(("agent_model", agent.model))
        
        # Update each component
        for comp_type, comp_value in components:
            key = f"{query_class.query_type}:{comp_type}:{comp_value}"
            
            if key not in self.component_effects:
                self.component_effects[key] = {"sum": 0.0, "count": 0, "sum_sq": 0.0}
            
            self.component_effects[key]["sum"] += outcome
            self.component_effects[key]["count"] += 1
            self.component_effects[key]["sum_sq"] += outcome ** 2
    
    def get_component_effect(
        self,
        query_type: str,
        component_type: str,
        component_value: str,
    ) -> ComponentEffect:
        """
        Get the estimated effect of a component.
        
        Args:
            query_type: Type of query
            component_type: Type of component (e.g., "agent_model")
            component_value: Value of the component
            
        Returns:
            ComponentEffect with statistics
        """
        key = f"{query_type}:{component_type}:{component_value}"
        data = self.component_effects.get(key, {"sum": 0.0, "count": 0, "sum_sq": 0.0})
        
        if data["count"] < 3:
            return ComponentEffect(
                component_type=component_type,
                component_value=component_value,
                effect_size=None,
                confidence="LOW",
                sample_size=data["count"],
            )
        
        mean = data["sum"] / data["count"]
        variance = (data["sum_sq"] / data["count"]) - (mean ** 2)
        std_dev = max(0, variance) ** 0.5
        
        confidence = "HIGH" if data["count"] > 50 else "MEDIUM" if data["count"] > 10 else "LOW"
        
        return ComponentEffect(
            component_type=component_type,
            component_value=component_value,
            effect_size=mean,
            confidence=confidence,
            sample_size=data["count"],
            std_dev=std_dev,
        )
    
    def get_best_components(
        self,
        query_type: str,
        component_type: str,
        top_n: int = 3,
    ) -> list[ComponentEffect]:
        """
        Get the best performing components of a type.
        
        Args:
            query_type: Type of query
            component_type: Type of component
            top_n: Number of top components to return
            
        Returns:
            List of best ComponentEffects
        """
        # Find all matching components
        prefix = f"{query_type}:{component_type}:"
        matching = []
        
        for key, data in self.component_effects.items():
            if key.startswith(prefix) and data["count"] >= 3:
                comp_value = key[len(prefix):]
                effect = self.get_component_effect(query_type, component_type, comp_value)
                if effect.effect_size is not None:
                    matching.append(effect)
        
        # Sort by effect size
        matching.sort(key=lambda e: e.effect_size or 0, reverse=True)
        
        return matching[:top_n]
    
    def get_insights(self, query_type: str = "general") -> dict:
        """
        Get optimization insights for a query type.
        
        Args:
            query_type: Type of query
            
        Returns:
            Dictionary of insights
        """
        return {
            "best_models": self.get_best_components(query_type, "agent_model"),
            "best_arbitrators": self.get_best_components(query_type, "arbitrator_model"),
            "best_num_rounds": self.get_best_components(query_type, "num_rounds"),
            "total_observations": len(self.observations),
            "unique_configs": len(self.posteriors),
        }
    
    def _config_signature(self, config: ConferenceConfig) -> str:
        """Create a hashable signature for a configuration."""
        agent_models = sorted(a.model for a in config.agents)
        return (
            f"{config.num_rounds}:{config.arbitrator.model}:"
            f"{','.join(agent_models)}"
        )
    
    def _save_to_storage(self):
        """Save optimizer state to storage."""
        if not self.storage_path:
            return
        
        try:
            state = {
                "posteriors": dict(self.posteriors),
                "component_effects": dict(self.component_effects),
                "observations": self.observations[-1000:],  # Keep last 1000
                "saved_at": datetime.now().isoformat(),
            }
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(state, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to save optimizer state: {e}")
    
    def _load_from_storage(self):
        """Load optimizer state from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text())
            
            # Restore posteriors
            for key, value in data.get("posteriors", {}).items():
                self.posteriors[key] = value
            
            # Restore component effects
            for key, value in data.get("component_effects", {}).items():
                self.component_effects[key] = value
            
            # Restore observations
            self.observations = data.get("observations", [])
            
            logger.info(
                f"Loaded optimizer state: {len(self.posteriors)} posteriors, "
                f"{len(self.observations)} observations"
            )
            
        except Exception as e:
            logger.error(f"Failed to load optimizer state: {e}")
    
    def get_stats(self) -> dict:
        """Get optimizer statistics."""
        return {
            "total_posteriors": len(self.posteriors),
            "total_components": len(self.component_effects),
            "total_observations": len(self.observations),
        }


class FeedbackCollector:
    """
    Collects and stores feedback for conferences.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the feedback collector.
        
        Args:
            storage_path: Path for persisting feedback
        """
        self.storage_path = storage_path
        self.feedback: dict[str, ConferenceFeedback] = {}
        
        if storage_path and storage_path.exists():
            self._load_from_storage()
    
    def get_or_create(self, conference_id: str) -> ConferenceFeedback:
        """Get or create feedback for a conference."""
        if conference_id not in self.feedback:
            self.feedback[conference_id] = ConferenceFeedback(
                conference_id=conference_id
            )
        return self.feedback[conference_id]
    
    def record_signal(self, conference_id: str, signal_type: str, value: float = 1.0):
        """Record a feedback signal."""
        from src.models.feedback import FeedbackSignal, SignalType
        
        fb = self.get_or_create(conference_id)
        fb.add_signal(FeedbackSignal(
            signal_type=SignalType(signal_type),
            value=value,
        ))
        self._save_to_storage()
    
    def record_immediate(self, conference_id: str, useful: str = None, will_act: str = None, dissent_useful: bool = None):
        """Record immediate feedback."""
        from src.models.feedback import ImmediateFeedback
        
        fb = self.get_or_create(conference_id)
        fb.add_immediate(ImmediateFeedback(
            useful=useful,
            will_act=will_act,
            dissent_useful=dissent_useful,
        ))
        self._save_to_storage()
    
    def record_delayed(self, conference_id: str, outcome: str, details: str = None):
        """Record delayed feedback."""
        from src.models.feedback import DelayedFeedback
        
        fb = self.get_or_create(conference_id)
        fb.add_delayed(DelayedFeedback(
            outcome=outcome,
            details=details,
        ))
        self._save_to_storage()
    
    def get_outcome(self, conference_id: str) -> Optional[float]:
        """Get the computed outcome score for a conference."""
        if conference_id in self.feedback:
            return self.feedback[conference_id].outcome_score
        return None
    
    def get_pending_followups(self, days_old: int = 14) -> list[str]:
        """Get conferences that need delayed follow-up."""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days_old)
        pending = []
        
        for conf_id, fb in self.feedback.items():
            if fb.delayed is None and fb.created_at < cutoff:
                pending.append(conf_id)
        
        return pending
    
    def _save_to_storage(self):
        """Save feedback to storage."""
        if not self.storage_path:
            return
        
        try:
            data = {
                conf_id: fb.model_dump(mode="json")
                for conf_id, fb in self.feedback.items()
            }
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
    
    def _load_from_storage(self):
        """Load feedback from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text())
            
            for conf_id, fb_data in data.items():
                self.feedback[conf_id] = ConferenceFeedback.model_validate(fb_data)
            
            logger.info(f"Loaded {len(self.feedback)} feedback records")
            
        except Exception as e:
            logger.error(f"Failed to load feedback: {e}")

