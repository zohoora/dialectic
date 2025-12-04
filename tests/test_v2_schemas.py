"""Tests for v2.1 Pydantic schemas."""

import pytest
from datetime import datetime

from src.models.v2_schemas import (
    # Enums
    ConferenceMode,
    Lane,
    EvidenceGrade,
    SpeculationStatus,
    CitationStatus,
    # Patient context
    PatientContext,
    # Routing
    RoutingDecision,
    # Scout
    ScoutCitation,
    ScoutReport,
    # Cross-examination
    Critique,
    FeasibilityAssessment,
    # Synthesis
    ClinicalConsensus,
    ExploratoryConsideration,
    Tension,
    ArbitratorSynthesis,
    # Speculation
    Speculation,
    WatchListTrigger,
    ValidationResult,
    # State
    LaneResult,
    V2ConferenceState,
    ClassifiedQuery,
)


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Tests for v2.1 enumerations."""

    def test_conference_mode_values(self):
        """Test ConferenceMode enum values."""
        assert ConferenceMode.STANDARD_CARE == "STANDARD_CARE"
        assert ConferenceMode.COMPLEX_DILEMMA == "COMPLEX_DILEMMA"
        assert ConferenceMode.NOVEL_RESEARCH == "NOVEL_RESEARCH"
        assert ConferenceMode.DIAGNOSTIC_PUZZLE == "DIAGNOSTIC_PUZZLE"

    def test_lane_values(self):
        """Test Lane enum values."""
        assert Lane.CLINICAL == "A"
        assert Lane.EXPLORATORY == "B"

    def test_evidence_grade_values(self):
        """Test EvidenceGrade enum values."""
        assert EvidenceGrade.META_ANALYSIS == "meta_analysis"
        assert EvidenceGrade.RCT_LARGE == "rct_large"
        assert EvidenceGrade.PREPRINT == "preprint"

    def test_speculation_status_values(self):
        """Test SpeculationStatus enum values."""
        assert SpeculationStatus.UNVERIFIED == "UNVERIFIED"
        assert SpeculationStatus.WATCHING == "WATCHING"
        assert SpeculationStatus.VALIDATED == "VALIDATED"


# =============================================================================
# PATIENT CONTEXT TESTS
# =============================================================================


class TestPatientContext:
    """Tests for PatientContext schema."""

    def test_minimal_creation(self):
        """Test creating PatientContext with minimal data."""
        context = PatientContext()
        
        assert context.age is None
        assert context.sex is None
        assert context.comorbidities == []

    def test_full_creation(self):
        """Test creating PatientContext with all fields."""
        context = PatientContext(
            age=55,
            sex="male",
            comorbidities=["diabetes", "hypertension"],
            current_medications=["metformin", "lisinopril"],
            allergies=["penicillin"],
            failed_treatments=["sulfonylurea"],
            relevant_history="Previous MI",
            constraints=["cost sensitive"],
        )
        
        assert context.age == 55
        assert context.sex == "male"
        assert len(context.comorbidities) == 2
        assert "penicillin" in context.allergies

    def test_age_validation(self):
        """Test age field validation."""
        # Valid ages
        PatientContext(age=0)
        PatientContext(age=150)
        
        # Invalid ages should raise
        with pytest.raises(ValueError):
            PatientContext(age=-1)
        with pytest.raises(ValueError):
            PatientContext(age=200)

    def test_sex_validation(self):
        """Test sex field validation."""
        # Valid values
        PatientContext(sex="male")
        PatientContext(sex="female")
        PatientContext(sex="other")
        
        # Invalid value should raise
        with pytest.raises(ValueError):
            PatientContext(sex="invalid")


# =============================================================================
# ROUTING DECISION TESTS
# =============================================================================


class TestRoutingDecision:
    """Tests for RoutingDecision schema."""

    def test_creation(self):
        """Test creating a RoutingDecision."""
        decision = RoutingDecision(
            mode=ConferenceMode.COMPLEX_DILEMMA,
            active_agents=["empiricist", "skeptic", "mechanist"],
            activate_scout=True,
            risk_profile=0.6,
        )
        
        assert decision.mode == ConferenceMode.COMPLEX_DILEMMA
        assert decision.activate_scout is True
        assert decision.risk_profile == 0.6

    def test_lane_a_agents_property(self):
        """Test lane_a_agents property."""
        decision = RoutingDecision(
            mode=ConferenceMode.COMPLEX_DILEMMA,
            active_agents=["empiricist", "skeptic", "pragmatist", "mechanist"],
            activate_scout=False,
        )
        
        lane_a = decision.lane_a_agents
        
        # Should only contain clinical agents
        assert "empiricist" in lane_a
        assert "skeptic" in lane_a
        assert "pragmatist" in lane_a
        assert "mechanist" not in lane_a

    def test_lane_b_agents_property(self):
        """Test lane_b_agents property."""
        decision = RoutingDecision(
            mode=ConferenceMode.NOVEL_RESEARCH,
            active_agents=["empiricist", "mechanist", "speculator"],
            activate_scout=True,
        )
        
        lane_b = decision.lane_b_agents
        
        # Should only contain exploratory agents
        assert "mechanist" in lane_b
        assert "speculator" in lane_b
        assert "empiricist" not in lane_b

    def test_risk_profile_validation(self):
        """Test risk_profile field validation."""
        # Valid values
        RoutingDecision(
            mode=ConferenceMode.STANDARD_CARE,
            active_agents=["empiricist"],
            activate_scout=False,
            risk_profile=0.0,
        )
        RoutingDecision(
            mode=ConferenceMode.STANDARD_CARE,
            active_agents=["empiricist"],
            activate_scout=False,
            risk_profile=1.0,
        )
        
        # Invalid values should raise
        with pytest.raises(ValueError):
            RoutingDecision(
                mode=ConferenceMode.STANDARD_CARE,
                active_agents=["empiricist"],
                activate_scout=False,
                risk_profile=-0.1,
            )


# =============================================================================
# SCOUT SCHEMAS TESTS
# =============================================================================


class TestScoutCitation:
    """Tests for ScoutCitation schema."""

    def test_minimal_creation(self):
        """Test creating ScoutCitation with minimal data."""
        citation = ScoutCitation(
            title="Test Study",
            year=2024,
            evidence_grade=EvidenceGrade.RCT_LARGE,
        )
        
        assert citation.title == "Test Study"
        assert citation.year == 2024
        assert citation.authors == []

    def test_full_creation(self):
        """Test creating ScoutCitation with all fields."""
        citation = ScoutCitation(
            title="Meta-analysis of treatment",
            authors=["Smith J", "Jones A"],
            journal="NEJM",
            year=2024,
            pmid="12345678",
            doi="10.1000/test",
            abstract="This study...",
            evidence_grade=EvidenceGrade.META_ANALYSIS,
            sample_size=1000,
            is_preprint=False,
            source_url="https://example.com",
            relevance_score=0.9,
            key_finding="Significant improvement",
            conflicts_with_consensus=False,
        )
        
        assert citation.pmid == "12345678"
        assert citation.sample_size == 1000
        assert citation.relevance_score == 0.9


class TestScoutReport:
    """Tests for ScoutReport schema."""

    def test_empty_report(self):
        """Test creating an empty Scout report."""
        report = ScoutReport(
            is_empty=True,
            query_keywords=["test"],
        )
        
        assert report.is_empty is True
        assert len(report.meta_analyses) == 0

    def test_report_with_findings(self):
        """Test creating Scout report with findings."""
        report = ScoutReport(
            is_empty=False,
            query_keywords=["diabetes", "treatment"],
            meta_analyses=[
                ScoutCitation(
                    title="Meta-analysis",
                    year=2024,
                    evidence_grade=EvidenceGrade.META_ANALYSIS,
                )
            ],
            high_quality_rcts=[
                ScoutCitation(
                    title="RCT",
                    year=2024,
                    evidence_grade=EvidenceGrade.RCT_LARGE,
                    sample_size=500,
                )
            ],
        )
        
        assert len(report.meta_analyses) == 1
        assert len(report.high_quality_rcts) == 1

    def test_to_context_block_empty(self):
        """Test context block for empty report."""
        report = ScoutReport(is_empty=True, query_keywords=[])
        block = report.to_context_block()
        
        assert "NO RECENT EVIDENCE" in block

    def test_to_context_block_with_findings(self):
        """Test context block with findings."""
        report = ScoutReport(
            is_empty=False,
            query_keywords=["test"],
            meta_analyses=[
                ScoutCitation(
                    title="Test Meta-analysis",
                    year=2024,
                    evidence_grade=EvidenceGrade.META_ANALYSIS,
                    key_finding="Important finding",
                    pmid="12345",
                )
            ],
        )
        
        block = report.to_context_block()
        
        assert "Meta-Analyses" in block or "Meta-analysis" in block
        assert "Test Meta-analysis" in block
        assert "12345" in block


# =============================================================================
# CRITIQUE AND ASSESSMENT TESTS
# =============================================================================


class TestCritique:
    """Tests for Critique schema."""

    def test_creation(self):
        """Test creating a Critique."""
        critique = Critique(
            critic_role="skeptic",
            target_role="speculator",
            target_lane=Lane.EXPLORATORY,
            critique_type="safety",
            content="Safety concerns about the proposal...",
            severity="major",
            specific_concerns=["Drug interaction", "Unknown long-term effects"],
        )
        
        assert critique.critic_role == "skeptic"
        assert critique.severity == "major"
        assert len(critique.specific_concerns) == 2


class TestFeasibilityAssessment:
    """Tests for FeasibilityAssessment schema."""

    def test_pragmatist_assessment(self):
        """Test creating a Pragmatist feasibility assessment."""
        assessment = FeasibilityAssessment(
            assessor_role="pragmatist",
            target_lane=Lane.CLINICAL,
            can_be_done=True,
            system_barriers=["Prior authorization required"],
            cost_concerns=["Not covered by all provinces"],
            overall_feasibility="possible",
            summary="Feasible with some barriers",
        )
        
        assert assessment.can_be_done is True
        assert assessment.overall_feasibility == "possible"

    def test_patient_voice_assessment(self):
        """Test creating a Patient Voice feasibility assessment."""
        assessment = FeasibilityAssessment(
            assessor_role="patient_voice",
            target_lane=Lane.EXPLORATORY,
            patient_burden="moderate",
            adherence_likelihood=0.7,
            qol_impact="May improve quality of life",
            patient_concerns=["Side effects", "Complexity"],
            overall_feasibility="possible",
            summary="Patient may accept with support",
        )
        
        assert assessment.patient_burden == "moderate"
        assert assessment.adherence_likelihood == 0.7


# =============================================================================
# SYNTHESIS TESTS
# =============================================================================


class TestClinicalConsensus:
    """Tests for ClinicalConsensus schema."""

    def test_creation(self):
        """Test creating a ClinicalConsensus."""
        consensus = ClinicalConsensus(
            recommendation="Recommend treatment A as first-line",
            evidence_basis=["Study 1", "Guideline X"],
            confidence=0.85,
            safety_profile="Generally well-tolerated",
            contraindications=["Renal impairment"],
            monitoring_required=["LFTs at 3 months"],
        )
        
        assert consensus.confidence == 0.85
        assert len(consensus.evidence_basis) == 2


class TestExploratoryConsideration:
    """Tests for ExploratoryConsideration schema."""

    def test_creation(self):
        """Test creating an ExploratoryConsideration."""
        consideration = ExploratoryConsideration(
            hypothesis="Drug X may work via novel pathway",
            mechanism="Blocks receptor Y",
            evidence_level="preclinical",
            potential_benefit="May help refractory cases",
            risks=["Unknown safety profile"],
            what_would_validate="RCT in target population",
        )
        
        assert consideration.evidence_level == "preclinical"
        assert consideration.is_hypothesis is True


class TestTension:
    """Tests for Tension schema."""

    def test_creation(self):
        """Test creating a Tension."""
        tension = Tension(
            description="Standard vs novel approach",
            lane_a_position="Stick with evidence-based treatment",
            lane_b_position="Try novel mechanism-based approach",
            resolution="unresolved",
            resolution_rationale="Depends on patient risk tolerance",
        )
        
        assert tension.resolution == "unresolved"


class TestArbitratorSynthesis:
    """Tests for ArbitratorSynthesis schema."""

    def test_creation(self):
        """Test creating an ArbitratorSynthesis."""
        synthesis = ArbitratorSynthesis(
            clinical_consensus=ClinicalConsensus(
                recommendation="Standard treatment",
                confidence=0.8,
            ),
            exploratory_considerations=[
                ExploratoryConsideration(
                    hypothesis="Novel approach",
                    evidence_level="theoretical",
                )
            ],
            tensions=[
                Tension(
                    description="Standard vs novel",
                    resolution="unresolved",
                )
            ],
            safety_concerns_raised=["Drug interaction risk"],
            stagnation_concerns_raised=["May miss better option"],
            what_would_change_mind="New RCT showing superiority",
            preserved_dissent=["Skeptic maintains concerns"],
            overall_confidence=0.75,
        )
        
        assert synthesis.overall_confidence == 0.75
        assert len(synthesis.exploratory_considerations) == 1


# =============================================================================
# SPECULATION TESTS
# =============================================================================


class TestSpeculation:
    """Tests for Speculation schema."""

    def test_creation(self):
        """Test creating a Speculation."""
        spec = Speculation(
            origin_conference_id="conf_123",
            origin_query="Treatment for condition X",
            hypothesis="Drug Y may help via mechanism Z",
            mechanism="Blocks receptor A",
            source_agent="speculator",
            initial_confidence="low",
            validation_criteria="RCT showing efficacy",
            watch_keywords=["Drug Y", "receptor A"],
        )
        
        assert spec.speculation_id is not None
        assert spec.status == SpeculationStatus.UNVERIFIED
        assert len(spec.watch_keywords) == 2

    def test_default_values(self):
        """Test default values."""
        spec = Speculation(
            hypothesis="Test hypothesis",
        )
        
        assert spec.status == SpeculationStatus.UNVERIFIED
        assert spec.promoted_to_experience_library is False


class TestWatchListTrigger:
    """Tests for WatchListTrigger schema."""

    def test_creation(self):
        """Test creating a WatchListTrigger."""
        trigger = WatchListTrigger(
            speculation_id="spec_123",
            matching_citations=[
                ScoutCitation(
                    title="Matching study",
                    year=2024,
                    evidence_grade=EvidenceGrade.RCT_SMALL,
                )
            ],
            match_quality="partial",
        )
        
        assert trigger.requires_human_review is True
        assert trigger.match_quality == "partial"


class TestValidationResult:
    """Tests for ValidationResult schema."""

    def test_creation(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(
            speculation_id="spec_123",
            new_evidence=[
                ScoutCitation(
                    title="New evidence",
                    year=2024,
                    evidence_grade=EvidenceGrade.RCT_LARGE,
                )
            ],
            support_level="partially_supports",
            evidence_quality=EvidenceGrade.RCT_LARGE,
            action="upgrade_status",
            new_status=SpeculationStatus.PARTIALLY_VALIDATED,
            validation_notes="Promising but needs more data",
        )
        
        assert result.action == "upgrade_status"
        assert result.new_status == SpeculationStatus.PARTIALLY_VALIDATED


# =============================================================================
# STATE TESTS
# =============================================================================


class TestLaneResult:
    """Tests for LaneResult schema."""

    def test_creation(self):
        """Test creating a LaneResult."""
        result = LaneResult(
            lane=Lane.CLINICAL,
            agent_responses={"empiricist_1": {"content": "Response"}},
        )
        
        assert result.lane == Lane.CLINICAL


class TestV2ConferenceState:
    """Tests for V2ConferenceState schema."""

    def test_creation(self):
        """Test creating a V2ConferenceState."""
        state = V2ConferenceState(
            query="Test clinical question",
            patient_context=PatientContext(age=55),
        )
        
        assert state.query == "Test clinical question"
        assert state.current_phase == "init"
        assert state.errors == []

    def test_full_state(self):
        """Test creating a complete state object."""
        state = V2ConferenceState(
            query="Complex query",
            patient_context=PatientContext(age=65, sex="female"),
            routing_decision=RoutingDecision(
                mode=ConferenceMode.COMPLEX_DILEMMA,
                active_agents=["empiricist"],
                activate_scout=True,
            ),
            scout_report=ScoutReport(is_empty=True, query_keywords=[]),
            lane_a_result=LaneResult(lane=Lane.CLINICAL),
            lane_b_result=LaneResult(lane=Lane.EXPLORATORY),
            current_phase="synthesis",
        )
        
        assert state.routing_decision.mode == ConferenceMode.COMPLEX_DILEMMA
        assert state.current_phase == "synthesis"


class TestClassifiedQuery:
    """Tests for ClassifiedQuery schema."""

    def test_creation(self):
        """Test creating a ClassifiedQuery."""
        query = ClassifiedQuery(
            raw_text="What is the treatment for diabetes?",
            query_type="THERAPEUTIC_SELECTION",
            subtags=["diabetes", "treatment"],
            classification_confidence=0.9,
        )
        
        assert query.query_id is not None
        assert query.raw_text == "What is the treatment for diabetes?"
        assert query.classification_confidence == 0.9

