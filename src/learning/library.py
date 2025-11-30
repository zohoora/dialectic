"""
Experience Library - Storage and retrieval of heuristics.

Stores generalizable heuristics extracted from high-quality conferences
and retrieves relevant ones for injection into new conferences.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src.models.experience import (
    CollisionType,
    ContextVector,
    HeuristicCollision,
    HeuristicStatus,
    InjectionContext,
    InjectionResult,
    ReasoningArtifact,
)


logger = logging.getLogger(__name__)


class ExperienceLibrary:
    """
    In-memory experience library with JSON file persistence.
    
    Stores heuristics and provides retrieval based on similarity
    to new queries.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the Experience Library.
        
        Args:
            storage_path: Path to JSON file for persistence (optional)
        """
        self.storage_path = storage_path
        self.heuristics: dict[str, ReasoningArtifact] = {}
        
        # Load from storage if exists
        if storage_path and storage_path.exists():
            self._load_from_storage()
    
    def add(self, artifact: ReasoningArtifact) -> str:
        """
        Add a heuristic to the library.
        
        Args:
            artifact: The heuristic to add
            
        Returns:
            The heuristic ID
        """
        self.heuristics[artifact.heuristic_id] = artifact
        self._save_to_storage()
        
        logger.info(
            f"Added heuristic {artifact.heuristic_id} to library "
            f"(domain: {artifact.context_vector.domain})"
        )
        
        return artifact.heuristic_id
    
    def get(self, heuristic_id: str) -> Optional[ReasoningArtifact]:
        """
        Get a specific heuristic by ID.
        
        Args:
            heuristic_id: ID of the heuristic
            
        Returns:
            The heuristic if found, None otherwise
        """
        return self.heuristics.get(heuristic_id)
    
    def remove(self, heuristic_id: str) -> bool:
        """
        Remove a heuristic from the library.
        
        Args:
            heuristic_id: ID of the heuristic to remove
            
        Returns:
            True if removed, False if not found
        """
        if heuristic_id in self.heuristics:
            del self.heuristics[heuristic_id]
            self._save_to_storage()
            logger.info(f"Removed heuristic {heuristic_id} from library")
            return True
        return False
    
    def update_status(
        self,
        heuristic_id: str,
        status: HeuristicStatus,
        superseded_by: Optional[str] = None,
    ) -> bool:
        """
        Update the status of a heuristic.
        
        Args:
            heuristic_id: ID of the heuristic
            status: New status
            superseded_by: ID of superseding heuristic (if applicable)
            
        Returns:
            True if updated, False if not found
        """
        if heuristic_id in self.heuristics:
            self.heuristics[heuristic_id].status = status
            if superseded_by:
                self.heuristics[heuristic_id].superseded_by = superseded_by
            self._save_to_storage()
            return True
        return False
    
    def record_usage(
        self,
        heuristic_id: str,
        outcome: str,  # "accepted", "rejected", "modified"
    ):
        """
        Record usage outcome for a heuristic.
        
        Args:
            heuristic_id: ID of the heuristic
            outcome: How the heuristic was used
        """
        if heuristic_id not in self.heuristics:
            return
        
        h = self.heuristics[heuristic_id]
        h.times_injected += 1
        
        if outcome == "accepted":
            h.times_accepted += 1
        elif outcome == "rejected":
            h.times_rejected += 1
        elif outcome == "modified":
            h.times_modified += 1
        
        self._save_to_storage()
    
    def search(
        self,
        context: InjectionContext,
        max_results: int = 3,
    ) -> list[ReasoningArtifact]:
        """
        Search for relevant heuristics based on context.
        
        Uses simple keyword matching for MVP. Can be upgraded to
        embedding-based similarity later.
        
        Args:
            context: The context to search for
            max_results: Maximum results to return
            
        Returns:
            List of matching heuristics, sorted by relevance
        """
        # Filter to active heuristics only
        active = [
            h for h in self.heuristics.values()
            if h.status == HeuristicStatus.ACTIVE
        ]
        
        if not active:
            return []
        
        # Score each heuristic
        scored = []
        query_lower = context.query.lower()
        
        for h in active:
            score = self._score_relevance(h, context, query_lower)
            if score > 0:
                scored.append((score, h))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [h for _, h in scored[:max_results]]
    
    def _score_relevance(
        self,
        heuristic: ReasoningArtifact,
        context: InjectionContext,
        query_lower: str,
    ) -> float:
        """
        Score relevance of a heuristic to a context.
        
        Simple keyword-based scoring for MVP.
        """
        score = 0.0
        cv = heuristic.context_vector
        
        # Domain match
        if context.domain and cv.domain:
            if context.domain.lower() == cv.domain.lower():
                score += 3.0
        
        # Keyword matches
        for keyword in cv.keywords:
            if keyword.lower() in query_lower:
                score += 1.0
        
        # Condition match
        if cv.condition.lower() in query_lower:
            score += 2.0
        
        # Treatment type in query
        if cv.treatment_type and cv.treatment_type.lower() in query_lower:
            score += 0.5
        
        # Patient factors
        for factor in context.patient_factors:
            if factor.lower() in [f.lower() for f in cv.patient_factors]:
                score += 1.5
        
        # Boost well-validated heuristics
        if heuristic.is_well_validated:
            score *= 1.2
        
        return score
    
    def get_injection(self, context: InjectionContext) -> InjectionResult:
        """
        Get heuristics for injection into a new conference.
        
        Args:
            context: The context for the new conference
            
        Returns:
            InjectionResult with heuristics and formatted prompt
        """
        # Search for relevant heuristics
        matches = self.search(context, max_results=3)
        
        # Count heuristics in domain
        domain_count = sum(
            1 for h in self.heuristics.values()
            if h.context_vector.domain == context.domain
            and h.status == HeuristicStatus.ACTIVE
        )
        
        # Genesis mode if no matches
        if not matches:
            return InjectionResult(
                heuristics_found=0,
                heuristics=[],
                genesis_mode=True,
                domain_coverage=domain_count,
                injection_prompt=self._build_genesis_prompt(context, domain_count),
            )
        
        # Check for collisions between top matches
        collision = None
        if len(matches) >= 2:
            collision = self._detect_collision(matches[0], matches[1])
        
        # Build injection prompt
        if collision:
            injection_prompt = self._build_collision_prompt(
                matches[:2], collision
            )
        else:
            injection_prompt = self._build_single_prompt(matches[0])
        
        return InjectionResult(
            heuristics_found=len(matches),
            heuristics=matches,
            collision=collision,
            injection_prompt=injection_prompt,
            domain_coverage=domain_count,
        )
    
    def _detect_collision(
        self,
        h1: ReasoningArtifact,
        h2: ReasoningArtifact,
    ) -> Optional[HeuristicCollision]:
        """
        Detect if two heuristics collide.
        
        Simple heuristic: if they have the same domain and condition
        but different recommendations.
        """
        cv1, cv2 = h1.context_vector, h2.context_vector
        
        # Same domain and condition
        if cv1.domain == cv2.domain and cv1.condition == cv2.condition:
            # Check if recommendations differ significantly
            # (Simple heuristic: check for key negation words)
            rec1_lower = h1.winning_heuristic.lower()
            rec2_lower = h2.winning_heuristic.lower()
            
            negation_words = ["not", "avoid", "don't", "never", "contraindicated"]
            
            h1_negative = any(w in rec1_lower for w in negation_words)
            h2_negative = any(w in rec2_lower for w in negation_words)
            
            if h1_negative != h2_negative:
                return HeuristicCollision(
                    heuristic_a_id=h1.heuristic_id,
                    heuristic_b_id=h2.heuristic_id,
                    collision_type=CollisionType.DIRECT_CONTRADICTION,
                    resolution_hint="One recommends while the other cautions against. Check qualifying conditions.",
                )
            
            # Different patient factors might indicate subset collision
            if set(cv1.patient_factors) != set(cv2.patient_factors):
                return HeuristicCollision(
                    heuristic_a_id=h1.heuristic_id,
                    heuristic_b_id=h2.heuristic_id,
                    collision_type=CollisionType.PATIENT_SUBSET,
                    resolution_hint="Heuristics apply to different patient populations. Determine which fits this patient.",
                )
        
        return None
    
    def _build_genesis_prompt(self, context: InjectionContext, domain_count: int) -> str:
        """Build prompt for genesis mode (no heuristics found)."""
        coverage = "low" if domain_count < 10 else "moderate" if domain_count < 50 else "good"
        
        return f"""### 🧠 Experience Library Retrieval

**System Note:** No relevant heuristics found for this query.
**Domain Coverage:** {domain_count} heuristics exist in this domain ({coverage} coverage)

**Task:** Reason from first principles. No prior patterns to build on.

**Note:** If this conference reaches a high-quality consensus, it may become 
the first heuristic for this query type. Reason carefully—you may be establishing precedent."""
    
    def _build_single_prompt(self, h: ReasoningArtifact) -> str:
        """Build prompt for single heuristic injection."""
        qualifying = "\n".join(f"- [ ] {c}" for c in h.qualifying_conditions) or "- None specified"
        disqualifying = "\n".join(f"- [ ] {c}" for c in h.disqualifying_conditions) or "- None specified"
        fragility = "\n".join(f"- {f}" for f in h.fragility_factors) or "- None identified"
        
        return f"""### 🧠 Experience Library Retrieval
**System Note:** A relevant heuristic was found from a past consensus.
**Warning:** This is a *hypothesis*, not a command.

**Heuristic ID:** {h.heuristic_id}
**Confidence:** {h.confidence:.0%} | **Validations:** {h.times_accepted}/{h.times_injected}

**Heuristic:** "{h.winning_heuristic}"

**Context:** {h.context_vector.domain} / {h.context_vector.condition}

**Qualifying Conditions (YOU MUST VALIDATE):**
{qualifying}

**Disqualifying Conditions (CHECK FOR PRESENCE):**
{disqualifying}

**Known Fragility Factors:**
{fragility}

**MANDATORY:** Before incorporating or rejecting this heuristic, explicitly validate 
each condition against the current patient and document your reasoning."""
    
    def _build_collision_prompt(
        self,
        heuristics: list[ReasoningArtifact],
        collision: HeuristicCollision,
    ) -> str:
        """Build prompt for multiple heuristics with collision."""
        h1, h2 = heuristics[0], heuristics[1]
        
        return f"""### 🧠 Experience Library Retrieval (Multiple Heuristics)

**⚠️ COLLISION DETECTED** between Heuristic A and Heuristic B
**Collision Type:** {collision.collision_type.value}
**Resolution Hint:** {collision.resolution_hint}

---

**Heuristic A** (ID: {h1.heuristic_id})
**Confidence:** {h1.confidence:.0%} | **Validations:** {h1.times_accepted}/{h1.times_injected}
**Heuristic:** "{h1.winning_heuristic}"
**Qualifying:** {', '.join(h1.qualifying_conditions) or 'None'}
**Disqualifying:** {', '.join(h1.disqualifying_conditions) or 'None'}

---

**Heuristic B** (ID: {h2.heuristic_id})
**Confidence:** {h2.confidence:.0%} | **Validations:** {h2.times_accepted}/{h2.times_injected}
**Heuristic:** "{h2.winning_heuristic}"
**Qualifying:** {', '.join(h2.qualifying_conditions) or 'None'}
**Disqualifying:** {', '.join(h2.disqualifying_conditions) or 'None'}

---

**MANDATORY:** You must validate EACH heuristic independently. If both validate, 
explicitly argue which applies to this patient and why. If the conflict cannot 
be resolved, flag as "Genuine Clinical Equipoise.\""""
    
    def get_stats(self) -> dict:
        """Get library statistics."""
        active = sum(
            1 for h in self.heuristics.values()
            if h.status == HeuristicStatus.ACTIVE
        )
        
        # Count by domain
        domains: dict[str, int] = {}
        for h in self.heuristics.values():
            domain = h.context_vector.domain
            domains[domain] = domains.get(domain, 0) + 1
        
        return {
            "total_heuristics": len(self.heuristics),
            "active_heuristics": active,
            "domains": domains,
            "well_validated": sum(
                1 for h in self.heuristics.values() if h.is_well_validated
            ),
        }
    
    def _save_to_storage(self):
        """Save library to JSON file."""
        if not self.storage_path:
            return
        
        try:
            data = {
                hid: h.model_dump(mode="json")
                for hid, h in self.heuristics.items()
            }
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to save library: {e}")
    
    def _load_from_storage(self):
        """Load library from JSON file."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text())
            
            for hid, hdata in data.items():
                self.heuristics[hid] = ReasoningArtifact.model_validate(hdata)
            
            logger.info(f"Loaded {len(self.heuristics)} heuristics from storage")
            
        except Exception as e:
            logger.error(f"Failed to load library: {e}")

