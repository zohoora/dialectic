"""
Query Classifier - Categorize incoming queries for configuration and retrieval.

Classifies queries by:
- Type (diagnostic, therapeutic, mechanism, risk, procedural, etc.)
- Domain (pain, cardiology, psychiatry, etc.)
- Complexity (low, medium, high)
- Uncertainty domain (mechanism known/unknown, outcomes known/unknown)
"""

import logging
import re
from typing import Optional, Protocol

from pydantic import BaseModel, Field

from src.models.conference import LLMResponse


logger = logging.getLogger(__name__)


class QueryType:
    """Query type taxonomy."""
    
    DIAGNOSTIC_DILEMMA = "diagnostic_dilemma"
    THERAPEUTIC_SELECTION = "therapeutic_selection"
    MECHANISM_EXPLANATION = "mechanism_explanation"
    RISK_ASSESSMENT = "risk_assessment"
    PROGNOSTIC = "prognostic"
    PROCEDURAL = "procedural"
    ETHICAL_VALUES = "ethical_values"
    GENERAL = "general"


class UncertaintyDomain:
    """Uncertainty domain classifications."""
    
    BOTH_KNOWN = "both_known"  # Standard medicine
    MECHANISM_KNOWN_OUTCOMES_UNCERTAIN = "mechanism_known_outcomes_uncertain"
    MECHANISM_UNCERTAIN_OUTCOMES_KNOWN = "mechanism_uncertain_outcomes_known"
    BOTH_UNCERTAIN = "both_uncertain"  # Experimental territory


class ClassifiedQuery(BaseModel):
    """A classified query with metadata for routing."""
    
    raw_text: str = Field(..., description="Original query text")
    query_type: str = Field(
        default=QueryType.GENERAL,
        description="Primary query type"
    )
    domain: str = Field(
        default="general",
        description="Medical domain (e.g., pain, cardiology)"
    )
    subtags: list[str] = Field(
        default_factory=list,
        description="Additional tags (e.g., chronic_pain, off_label)"
    )
    complexity: str = Field(
        default="medium",
        description="low, medium, high"
    )
    uncertainty_domain: str = Field(
        default=UncertaintyDomain.BOTH_KNOWN,
        description="Uncertainty characterization"
    )
    classification_confidence: float = Field(
        default=0.5,
        description="Confidence in classification (0-1)"
    )
    extracted_entities: dict = Field(
        default_factory=dict,
        description="Extracted entities (conditions, drugs, patient features)"
    )
    
    def signature(self) -> str:
        """Create a signature for bandit optimization."""
        return f"{self.query_type}:{self.domain}:{self.complexity}"


class LLMClientProtocol(Protocol):
    """Protocol for LLM client."""
    
    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        ...


class QueryClassifier:
    """
    Classifies queries using a combination of rules and LLM.
    
    Phase 1 (current): Rule-based + keyword matching
    Future: LLM-based classification with structured output
    """
    
    # Domain keywords
    DOMAIN_KEYWORDS = {
        "pain": ["pain", "crps", "neuropath", "fibromyalgia", "headache", "migraine", 
                 "analgesic", "opioid", "nsaid", "gabapentin", "lyrica", "nerve block"],
        "cardiology": ["heart", "cardiac", "cardiovascular", "arrhythmia", "hypertension",
                      "blood pressure", "cholesterol", "statin", "anticoagul", "afib"],
        "psychiatry": ["depression", "anxiety", "bipolar", "schizophren", "ssri", "antidepressant",
                      "mood", "psychosis", "ptsd", "ocd"],
        "neurology": ["seizure", "epilepsy", "stroke", "parkinson", "alzheimer", "dementia",
                     "multiple sclerosis", "neuropathy", "brain"],
        "oncology": ["cancer", "tumor", "chemotherapy", "radiation", "oncolog", "malignant",
                    "metastatic", "carcinoma", "lymphoma", "leukemia"],
        "endocrinology": ["diabetes", "thyroid", "hormone", "insulin", "glucose", "hba1c",
                         "adrenal", "pituitary", "testosterone", "estrogen"],
        "rheumatology": ["arthritis", "lupus", "rheumatoid", "autoimmune", "joint",
                        "inflammation", "connective tissue"],
        "infectious": ["infection", "antibiotic", "virus", "bacteria", "sepsis",
                      "pneumonia", "hiv", "hepatitis"],
        "pulmonology": ["lung", "respiratory", "asthma", "copd", "pulmonary", "breathing",
                       "oxygen", "ventilat"],
        "gastroenterology": ["gi", "stomach", "intestin", "liver", "hepat", "pancrea",
                            "colon", "ibd", "crohn", "ulcer"],
    }
    
    # Query type patterns
    TYPE_PATTERNS = {
        QueryType.DIAGNOSTIC_DILEMMA: [
            r"what('s| is) causing",
            r"diagnos(e|is)",
            r"what could (be|explain)",
            r"differential",
            r"why (does|is) (the|this) patient",
            r"work.?up",
        ],
        QueryType.THERAPEUTIC_SELECTION: [
            r"(best|optimal|recommended) (treatment|therapy|medication)",
            r"what (should|would) (you|i|we) (treat|prescribe|recommend)",
            r"treatment (for|of|approach)",
            r"how (to|should|would) (treat|manage)",
            r"first.?line",
            r"should (i|we) (start|try|use)",
        ],
        QueryType.MECHANISM_EXPLANATION: [
            r"(how|why) does .* (work|help|affect)",
            r"mechanism (of|behind)",
            r"explain (how|why)",
            r"pathophysiology",
            r"what('s| is) the (mechanism|reason)",
        ],
        QueryType.RISK_ASSESSMENT: [
            r"(is it|are there) (safe|risk|danger)",
            r"(side effect|adverse|interaction)",
            r"(contraindic|precaution)",
            r"(combine|combining|combination) .* (safe|risk)",
            r"(risk|safe) (to|of)",
        ],
        QueryType.PROGNOSTIC: [
            r"prognos(is|tic)",
            r"(what|how) (is|will) .* (outcome|course|progress)",
            r"(expected|likely) (outcome|course)",
            r"how long (will|does)",
            r"(recover|remission)",
        ],
        QueryType.PROCEDURAL: [
            r"how (to|do i|should i) (perform|do|conduct)",
            r"step.?by.?step",
            r"technique (for|of)",
            r"procedure (for|of)",
            r"protocol (for|of)",
        ],
        QueryType.ETHICAL_VALUES: [
            r"(should|ethical|moral)",
            r"(quality of life|end of life)",
            r"(aggressive|palliative|comfort) (treatment|care)",
            r"(withdraw|withhold)",
            r"patient (wish|prefer|autonom)",
        ],
    }
    
    # Complexity indicators
    HIGH_COMPLEXITY_KEYWORDS = [
        "multiple", "comorbid", "complex", "refractory", "failed", "resistant",
        "polypharmacy", "contraindicated", "allerg", "intolerant", "rare",
        "atypical", "unusual", "conflicting", "uncertain", "controversial",
    ]
    
    LOW_COMPLEXITY_KEYWORDS = [
        "simple", "straightforward", "typical", "common", "standard",
        "first-line", "uncomplicated", "mild",
    ]
    
    def __init__(self, llm_client: Optional[LLMClientProtocol] = None):
        """
        Initialize the classifier.
        
        Args:
            llm_client: Optional LLM client for advanced classification
        """
        self.llm_client = llm_client
    
    def classify(self, query: str) -> ClassifiedQuery:
        """
        Classify a query using rule-based approach.
        
        Args:
            query: Raw query text
            
        Returns:
            ClassifiedQuery with all metadata
        """
        query_lower = query.lower()
        
        # Determine query type
        query_type = self._classify_type(query_lower)
        
        # Determine domain
        domain = self._classify_domain(query_lower)
        
        # Determine complexity
        complexity = self._classify_complexity(query_lower)
        
        # Extract subtags
        subtags = self._extract_subtags(query_lower)
        
        # Determine uncertainty domain
        uncertainty = self._classify_uncertainty(query_lower, subtags)
        
        # Extract entities (basic)
        entities = self._extract_entities(query)
        
        # Calculate confidence based on how many signals we matched
        confidence = self._calculate_confidence(query_type, domain, complexity)
        
        return ClassifiedQuery(
            raw_text=query,
            query_type=query_type,
            domain=domain,
            subtags=subtags,
            complexity=complexity,
            uncertainty_domain=uncertainty,
            classification_confidence=confidence,
            extracted_entities=entities,
        )
    
    def _classify_type(self, query_lower: str) -> str:
        """Classify query type based on patterns."""
        scores = {}
        
        for query_type, patterns in self.TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[query_type] = score
        
        if not scores:
            return QueryType.GENERAL
        
        return max(scores, key=scores.get)
    
    def _classify_domain(self, query_lower: str) -> str:
        """Classify medical domain based on keywords."""
        scores = {}
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[domain] = score
        
        if not scores:
            return "general"
        
        return max(scores, key=scores.get)
    
    def _classify_complexity(self, query_lower: str) -> str:
        """Classify query complexity."""
        high_count = sum(1 for kw in self.HIGH_COMPLEXITY_KEYWORDS if kw in query_lower)
        low_count = sum(1 for kw in self.LOW_COMPLEXITY_KEYWORDS if kw in query_lower)
        
        # Also consider query length as proxy for complexity
        word_count = len(query_lower.split())
        
        if high_count >= 2 or word_count > 100:
            return "high"
        elif low_count >= 2 or word_count < 20:
            return "low"
        else:
            return "medium"
    
    def _extract_subtags(self, query_lower: str) -> list[str]:
        """Extract relevant subtags from query."""
        subtags = []
        
        # Pain-related
        if "chronic" in query_lower and "pain" in query_lower:
            subtags.append("chronic_pain")
        if "acute" in query_lower and "pain" in query_lower:
            subtags.append("acute_pain")
        if any(w in query_lower for w in ["neuropath", "nerve"]):
            subtags.append("neuropathic")
        
        # Treatment type
        if any(w in query_lower for w in ["drug", "medication", "prescri", "dose"]):
            subtags.append("pharmacological")
        if any(w in query_lower for w in ["procedure", "intervention", "inject", "block", "surgery"]):
            subtags.append("interventional")
        
        # Special populations
        if any(w in query_lower for w in ["child", "pediatric", "infant"]):
            subtags.append("pediatric")
        if any(w in query_lower for w in ["elderly", "geriatric", "older", "aged"]):
            subtags.append("geriatric")
        if any(w in query_lower for w in ["pregnan", "breastfeed", "lactati"]):
            subtags.append("pregnancy")
        
        # Evidence status
        if any(w in query_lower for w in ["off-label", "off label", "offlabel", "experimental", "novel"]):
            subtags.append("off_label")
        if any(w in query_lower for w in ["sparse", "limited evidence", "few studies"]):
            subtags.append("evidence_sparse")
        if any(w in query_lower for w in ["conflict", "controver", "debat"]):
            subtags.append("evidence_conflicting")
        
        # Urgency
        if any(w in query_lower for w in ["urgent", "emergenc", "immediate", "acute"]):
            subtags.append("time_sensitive")
        
        return subtags
    
    def _classify_uncertainty(self, query_lower: str, subtags: list[str]) -> str:
        """Classify uncertainty domain."""
        # Check for explicit uncertainty markers
        evidence_sparse = "evidence_sparse" in subtags
        evidence_conflicting = "evidence_conflicting" in subtags
        off_label = "off_label" in subtags
        
        mechanism_uncertain = any(w in query_lower for w in [
            "unknown mechanism", "unclear how", "not well understood",
        ])
        
        outcome_uncertain = any(w in query_lower for w in [
            "limited data", "unclear efficacy", "variable response",
        ]) or evidence_sparse
        
        if mechanism_uncertain and outcome_uncertain:
            return UncertaintyDomain.BOTH_UNCERTAIN
        elif mechanism_uncertain:
            return UncertaintyDomain.MECHANISM_UNCERTAIN_OUTCOMES_KNOWN
        elif outcome_uncertain or off_label:
            return UncertaintyDomain.MECHANISM_KNOWN_OUTCOMES_UNCERTAIN
        else:
            return UncertaintyDomain.BOTH_KNOWN
    
    def _extract_entities(self, query: str) -> dict:
        """Extract basic entities from query (simplified)."""
        entities = {
            "conditions": [],
            "drugs": [],
            "patient_features": [],
        }
        
        # Common drug suffixes
        drug_patterns = [
            r'\b\w+(?:ine|ide|ole|ine|ol|am|il|an|er|in|ix|ex|ax|ox|ux)\b',
        ]
        
        # Age patterns
        age_match = re.search(r'(\d{1,3})[\s-]*(year|yo|y\.?o\.?|years?\s*old)', query, re.IGNORECASE)
        if age_match:
            entities["patient_features"].append(f"age_{age_match.group(1)}")
        
        # Gender patterns
        if re.search(r'\b(male|man|men|boy)\b', query, re.IGNORECASE):
            entities["patient_features"].append("male")
        if re.search(r'\b(female|woman|women|girl)\b', query, re.IGNORECASE):
            entities["patient_features"].append("female")
        
        return entities
    
    def _calculate_confidence(self, query_type: str, domain: str, complexity: str) -> float:
        """Calculate confidence in classification."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if we matched a specific type (not general)
        if query_type != QueryType.GENERAL:
            confidence += 0.2
        
        # Higher confidence if we identified a domain
        if domain != "general":
            confidence += 0.2
        
        # Slight boost for clear complexity signals
        if complexity != "medium":
            confidence += 0.05
        
        return min(0.95, confidence)
    
    async def classify_with_llm(self, query: str, model: str = "anthropic/claude-3-haiku") -> ClassifiedQuery:
        """
        Classify using LLM for higher accuracy (future enhancement).
        
        Args:
            query: Raw query text
            model: LLM model to use
            
        Returns:
            ClassifiedQuery with all metadata
        """
        if not self.llm_client:
            return self.classify(query)
        
        # For now, fall back to rule-based
        # Future: implement LLM-based classification
        return self.classify(query)

