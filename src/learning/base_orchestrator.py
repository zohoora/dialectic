"""
Base Orchestrator - Shared functionality for learning-enabled conference execution.

Provides common infrastructure used by orchestrator implementations.
"""

import logging
from pathlib import Path
from typing import Optional

from src.learning.classifier import ClassifiedQuery, QueryClassifier
from src.learning.gatekeeper import Gatekeeper
from src.learning.injector import HeuristicInjector
from src.learning.library import ExperienceLibrary
from src.learning.optimizer import ConfigurationOptimizer, FeedbackCollector
from src.learning.surgeon import Surgeon
from src.llm.client import LLMClient
from src.models.experience import InjectionResult


logger = logging.getLogger(__name__)


class BaseOrchestrator:
    """
    Base class for learning-enabled conference orchestrators.
    
    Provides shared functionality:
    - Component initialization
    - Feedback recording
    - Statistics
    - Heuristic outcome checking
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        data_dir: Optional[Path] = None,
        data_suffix: str = "",
    ):
        """
        Initialize the orchestrator with learning components.
        
        Args:
            llm_client: LLM client (created if not provided)
            data_dir: Directory for persistent storage
            data_suffix: Suffix for data file names (e.g., "_v3")
        """
        self.llm_client = llm_client or LLMClient()
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize learning components
        self._init_learning_components(data_suffix)
    
    def _init_learning_components(self, suffix: str = "") -> None:
        """
        Initialize all learning components.
        
        Args:
            suffix: Suffix for data file names
        """
        self.classifier = QueryClassifier(llm_client=self.llm_client)
        self.library = ExperienceLibrary(
            storage_path=self.data_dir / f"experience_library{suffix}.json"
        )
        self.optimizer = ConfigurationOptimizer(
            storage_path=self.data_dir / f"optimizer_state{suffix}.json"
        )
        self.feedback_collector = FeedbackCollector(
            storage_path=self.data_dir / f"feedback{suffix}.json"
        )
        self.injector = HeuristicInjector(self.library)
        self.gatekeeper = Gatekeeper()
        self.surgeon = Surgeon(self.llm_client)
    
    def record_feedback(
        self,
        conference_id: str,
        useful: Optional[str] = None,
        will_act: Optional[str] = None,
        dissent_useful: Optional[bool] = None,
    ) -> None:
        """
        Record immediate feedback for a conference.
        
        Args:
            conference_id: ID of the conference
            useful: "yes", "partially", "no"
            will_act: "yes", "modified", "no"
            dissent_useful: Whether dissent was useful
        """
        self.feedback_collector.record_immediate(
            conference_id,
            useful=useful,
            will_act=will_act,
            dissent_useful=dissent_useful,
        )
        
        # Update bandit if we have outcome
        outcome = self.feedback_collector.get_outcome(conference_id)
        if outcome is not None:
            logger.info(f"Feedback recorded for {conference_id}: outcome={outcome:.2f}")
    
    def get_stats(self) -> dict:
        """
        Get orchestrator statistics.
        
        Returns:
            Dict with library, optimizer, and feedback stats
        """
        return {
            "library_stats": self.library.get_stats(),
            "optimizer_stats": self.optimizer.get_stats(),
            "feedback_count": len(self.feedback_collector.feedback),
        }
    
    def _classify_query(self, query: str) -> ClassifiedQuery:
        """
        Classify a query for heuristic matching.
        
        Args:
            query: The clinical question
            
        Returns:
            ClassifiedQuery with type, domain, complexity
        """
        classification = self.classifier.classify(query)
        logger.info(
            f"Query classified: type={classification.query_type}, "
            f"domain={classification.domain}, complexity={classification.complexity}"
        )
        return classification
    
    def _get_heuristics(self, classification: ClassifiedQuery) -> InjectionResult:
        """
        Get relevant heuristics for a classified query.
        
        Args:
            classification: The classified query
            
        Returns:
            InjectionResult with matching heuristics
        """
        injection_result = self.injector.get_injection_for_query(classification)
        logger.info(
            f"Injection result: {len(injection_result.heuristics)} heuristics, "
            f"genesis={injection_result.genesis_mode}"
        )
        return injection_result
    
    def _check_heuristic_outcome_in_content(
        self,
        content: str,
        heuristic_id: str,
    ) -> Optional[str]:
        """
        Check how a heuristic was used based on response content.
        
        Args:
            content: Response content to search
            heuristic_id: ID of the heuristic to check
            
        Returns:
            "accepted", "rejected", "modified", or None
        """
        content_lower = content.lower()
        heuristic_lower = heuristic_id.lower()
        
        if heuristic_lower in content_lower or "heuristic" in content_lower:
            if "decision: incorporate" in content_lower or "accept" in content_lower:
                return "accepted"
            elif "decision: reject" in content_lower or "reject" in content_lower:
                return "rejected"
            elif "decision: modify" in content_lower or "modify" in content_lower:
                return "modified"
        
        return None

