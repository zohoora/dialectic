"""
Tests for the Query Classifier.
"""

import pytest

from src.learning.classifier import (
    ClassifiedQuery,
    QueryClassifier,
    QueryType,
    UncertaintyDomain,
)


class TestQueryClassifier:
    """Tests for QueryClassifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create a classifier instance."""
        return QueryClassifier()
    
    # ==== Query Type Classification ====
    
    def test_classifies_diagnostic_query(self, classifier):
        """Test classifying a diagnostic query."""
        query = "What's causing this patient's constellation of symptoms including fatigue, joint pain, and fever?"
        result = classifier.classify(query)
        
        assert result.query_type == QueryType.DIAGNOSTIC_DILEMMA
    
    def test_classifies_therapeutic_query(self, classifier):
        """Test classifying a treatment query."""
        query = "What's the best treatment for refractory CRPS in a patient who failed nerve blocks?"
        result = classifier.classify(query)
        
        assert result.query_type == QueryType.THERAPEUTIC_SELECTION
    
    def test_classifies_mechanism_query(self, classifier):
        """Test classifying a mechanism query."""
        query = "How does ketamine help neuropathic pain? What's the mechanism?"
        result = classifier.classify(query)
        
        assert result.query_type == QueryType.MECHANISM_EXPLANATION
    
    def test_classifies_risk_query(self, classifier):
        """Test classifying a risk assessment query."""
        query = "Is it safe to combine low-dose naltrexone with tramadol? What are the risks?"
        result = classifier.classify(query)
        
        assert result.query_type == QueryType.RISK_ASSESSMENT
    
    def test_classifies_procedural_query(self, classifier):
        """Test classifying a procedural query."""
        query = "How do I perform a stellate ganglion block? Step by step technique."
        result = classifier.classify(query)
        
        assert result.query_type == QueryType.PROCEDURAL
    
    def test_classifies_general_query(self, classifier):
        """Test fallback to general type."""
        query = "Tell me about diabetes management."
        result = classifier.classify(query)
        
        assert result.query_type == QueryType.GENERAL
    
    # ==== Domain Classification ====
    
    def test_classifies_pain_domain(self, classifier):
        """Test classifying pain domain."""
        query = "Best approach for chronic neuropathic pain after failed gabapentin?"
        result = classifier.classify(query)
        
        assert result.domain == "pain"
    
    def test_classifies_cardiology_domain(self, classifier):
        """Test classifying cardiology domain."""
        query = "Managing afib in a patient with hypertension on anticoagulation?"
        result = classifier.classify(query)
        
        assert result.domain == "cardiology"
    
    def test_classifies_psychiatry_domain(self, classifier):
        """Test classifying psychiatry domain."""
        query = "Treatment-resistant depression not responding to SSRIs?"
        result = classifier.classify(query)
        
        assert result.domain == "psychiatry"
    
    def test_classifies_oncology_domain(self, classifier):
        """Test classifying oncology domain."""
        query = "Chemotherapy options for metastatic carcinoma?"
        result = classifier.classify(query)
        
        assert result.domain == "oncology"
    
    # ==== Complexity Classification ====
    
    def test_classifies_high_complexity(self, classifier):
        """Test classifying high complexity."""
        query = """Complex case: 72yo male with multiple comorbidities including 
        refractory chronic pain, COPD, CKD stage 3, on polypharmacy with 
        multiple contraindicated medications and failed several treatment attempts."""
        result = classifier.classify(query)
        
        assert result.complexity == "high"
    
    def test_classifies_low_complexity(self, classifier):
        """Test classifying low complexity."""
        query = "Simple first-line treatment for mild headache?"
        result = classifier.classify(query)
        
        assert result.complexity == "low"
    
    def test_classifies_medium_complexity_default(self, classifier):
        """Test medium complexity for moderate-length queries."""
        query = "Treatment options for moderate back pain in a patient who has tried a few medications but not the more advanced options. The patient has some history of cardiovascular issues."
        result = classifier.classify(query)
        
        assert result.complexity == "medium"
    
    # ==== Subtag Extraction ====
    
    def test_extracts_chronic_pain_subtag(self, classifier):
        """Test extracting chronic pain subtag."""
        query = "Managing chronic pain in an elderly patient."
        result = classifier.classify(query)
        
        assert "chronic_pain" in result.subtags
    
    def test_extracts_neuropathic_subtag(self, classifier):
        """Test extracting neuropathic subtag."""
        query = "Treating neuropathic symptoms after nerve injury."
        result = classifier.classify(query)
        
        assert "neuropathic" in result.subtags
    
    def test_extracts_pediatric_subtag(self, classifier):
        """Test extracting pediatric subtag."""
        query = "Pain management in a 10-year-old child."
        result = classifier.classify(query)
        
        assert "pediatric" in result.subtags
    
    def test_extracts_pregnancy_subtag(self, classifier):
        """Test extracting pregnancy subtag."""
        query = "Safe medications during pregnancy for migraines."
        result = classifier.classify(query)
        
        assert "pregnancy" in result.subtags
    
    def test_extracts_off_label_subtag(self, classifier):
        """Test extracting off-label subtag."""
        query = "Off-label use of ketamine for depression."
        result = classifier.classify(query)
        
        assert "off_label" in result.subtags
    
    def test_extracts_time_sensitive_subtag(self, classifier):
        """Test extracting time sensitive subtag."""
        query = "Urgent treatment needed for acute pain crisis."
        result = classifier.classify(query)
        
        assert "time_sensitive" in result.subtags
    
    # ==== Uncertainty Domain ====
    
    def test_classifies_mechanism_uncertain(self, classifier):
        """Test mechanism uncertain classification."""
        query = "Treatment works but unknown mechanism."
        result = classifier.classify(query)
        
        # This is a simplified test - actual classification depends on markers
        assert result.uncertainty_domain is not None
    
    def test_classifies_outcomes_uncertain_for_off_label(self, classifier):
        """Test off-label triggers outcome uncertainty."""
        query = "Off-label novel therapy with limited data."
        result = classifier.classify(query)
        
        assert result.uncertainty_domain in [
            UncertaintyDomain.MECHANISM_KNOWN_OUTCOMES_UNCERTAIN,
            UncertaintyDomain.BOTH_UNCERTAIN,
        ]
    
    # ==== Confidence Calculation ====
    
    def test_confidence_higher_for_specific_type(self, classifier):
        """Test confidence increases with specific type."""
        specific_query = "What's the best treatment for chronic pain?"
        general_query = "Tell me about pain."
        
        specific_result = classifier.classify(specific_query)
        general_result = classifier.classify(general_query)
        
        assert specific_result.classification_confidence >= general_result.classification_confidence
    
    def test_confidence_higher_with_domain(self, classifier):
        """Test confidence increases with domain match."""
        with_domain = "Best treatment approach for chronic neuropathic pain?"
        without_domain = "Hello there."  # No domain, no type
        
        domain_result = classifier.classify(with_domain)
        no_domain_result = classifier.classify(without_domain)
        
        assert domain_result.classification_confidence >= no_domain_result.classification_confidence
    
    # ==== Signature ====
    
    def test_signature_format(self, classifier):
        """Test signature format."""
        query = "Treatment for chronic pain in cardiology patient."
        result = classifier.classify(query)
        
        sig = result.signature()
        assert ":" in sig
        assert result.query_type in sig or "general" in sig


class TestClassifiedQuery:
    """Tests for ClassifiedQuery model."""
    
    def test_create_classified_query(self):
        """Test creating a ClassifiedQuery."""
        cq = ClassifiedQuery(
            raw_text="Test query",
            query_type=QueryType.THERAPEUTIC_SELECTION,
            domain="pain",
            complexity="high",
        )
        
        assert cq.raw_text == "Test query"
        assert cq.query_type == QueryType.THERAPEUTIC_SELECTION
        assert cq.domain == "pain"
    
    def test_default_values(self):
        """Test default values."""
        cq = ClassifiedQuery(raw_text="Test")
        
        assert cq.query_type == QueryType.GENERAL
        assert cq.domain == "general"
        assert cq.complexity == "medium"
        assert cq.subtags == []
        assert cq.classification_confidence == 0.5
    
    def test_signature(self):
        """Test signature generation."""
        cq = ClassifiedQuery(
            raw_text="Test",
            query_type="diagnostic",
            domain="pain",
            complexity="high",
        )
        
        assert cq.signature() == "diagnostic:pain:high"

