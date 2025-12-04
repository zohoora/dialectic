"""
Pytest configuration and shared fixtures for the test suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from src.models.conference import (
    AgentConfig, AgentRole, ConferenceConfig, ConferenceResult,
    LLMResponse, ConferenceRound, ConferenceSynthesis, AgentResponse,
    ArbitratorConfig, TokenUsage, DissentRecord
)
from src.models.fragility import FragilityReport, FragilityResult, FragilityOutcome


# ============================================================================
# Mock LLM Client
# ============================================================================

@pytest.fixture
def mock_llm_response():
    """Factory for creating mock LLM responses."""
    def _create(content: str, model: str = "test-model", input_tokens: int = 100, output_tokens: int = 50):
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    return _create


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Create a mock LLM client that returns configurable responses."""
    client = MagicMock()
    client.complete = AsyncMock(return_value=mock_llm_response("Default mock response"))
    return client


# ============================================================================
# Conference Fixtures
# ============================================================================

@pytest.fixture
def sample_agent_configs():
    """Create sample agent configurations."""
    return [
        AgentConfig(
            agent_id="advocate_1",
            role=AgentRole.ADVOCATE,
            model="test-model",
        ),
        AgentConfig(
            agent_id="skeptic_1",
            role=AgentRole.SKEPTIC,
            model="test-model",
        ),
        AgentConfig(
            agent_id="empiricist_1",
            role=AgentRole.EMPIRICIST,
            model="test-model",
        ),
    ]


@pytest.fixture
def sample_conference_config(sample_agent_configs):
    """Create a sample conference configuration."""
    return ConferenceConfig(
        agents=sample_agent_configs,
        arbitrator=ArbitratorConfig(
            model="test-model",
        ),
        topology="free_discussion",
        num_rounds=2,
    )


@pytest.fixture
def sample_round_result():
    """Create a sample round result."""
    return ConferenceRound(
        round_number=1,
        agent_responses={
            "advocate_1": AgentResponse(
                agent_id="advocate_1",
                role=AgentRole.ADVOCATE,
                model="test-model",
                content="Consider metformin as first-line treatment.",
                confidence=0.8,
            ),
            "skeptic_1": AgentResponse(
                agent_id="skeptic_1",
                role=AgentRole.SKEPTIC,
                model="test-model",
                content="Agree with metformin. Monitor cardiac function.",
                confidence=0.75,
            ),
        }
    )


@pytest.fixture
def sample_synthesis_result():
    """Create a sample synthesis result."""
    return ConferenceSynthesis(
        final_consensus="Recommend metformin as first-line treatment with cardiac monitoring.",
        confidence=0.85,
        key_points=["Strong evidence base", "Well-tolerated"],
        evidence_summary="Strong evidence from UKPDS and ADA guidelines.",
        caveats=["Consider GLP-1 agonists for patients with high cardiovascular risk."],
    )


@pytest.fixture
def sample_conference_result(sample_round_result, sample_synthesis_result, sample_conference_config):
    """Create a sample conference result."""
    return ConferenceResult(
        conference_id="test-conference-123",
        query="What is the best first-line treatment for type 2 diabetes in a patient with cardiovascular disease?",
        config=sample_conference_config,
        rounds=[sample_round_result],
        synthesis=sample_synthesis_result,
        token_usage=TokenUsage(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_tokens=1500,
            estimated_cost_usd=0.05,
        ),
        dissent=DissentRecord(preserved=False),
    )


# ============================================================================
# Fragility Fixtures
# ============================================================================

@pytest.fixture
def sample_fragility_result():
    """Create a sample fragility test result."""
    return FragilityResult(
        perturbation="What if the patient has renal impairment?",
        explanation="The recommendation changed to account for renal dosing.",
        outcome=FragilityOutcome.MODIFIES,
        modified_recommendation="Recommend metformin with dose adjustment; avoid if GFR < 30.",
    )


@pytest.fixture
def sample_fragility_report(sample_fragility_result):
    """Create a sample fragility report.
    
    Note: survival_rate and fragility_level are computed properties,
    not constructor parameters.
    """
    return FragilityReport(
        results=[sample_fragility_result],
        perturbations_tested=1,
    )


# ============================================================================
# Experience/Heuristic Fixtures
# ============================================================================

# Note: InjectionResult is complex and varies by test - create inline in tests that need it


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def prompts_dir():
    """Return the path to the prompts directory."""
    return Path(__file__).parent.parent / "prompts"


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_pubmed_response():
    """Create a mock PubMed search response."""
    return {
        "esearchresult": {
            "count": "10",
            "idlist": ["12345678", "23456789", "34567890"],
        }
    }


@pytest.fixture
def mock_pubmed_summary():
    """Create a mock PubMed summary response."""
    return {
        "result": {
            "12345678": {
                "uid": "12345678",
                "title": "Metformin in Type 2 Diabetes",
                "authors": [{"name": "Smith J"}, {"name": "Jones A"}],
                "source": "Diabetes Care",
                "pubdate": "2023",
            }
        }
    }


# ============================================================================
# v2.1 Fixtures
# ============================================================================

from src.models.v2_schemas import (
    ConferenceMode,
    Lane,
    EvidenceGrade,
    PatientContext,
    RoutingDecision,
    ScoutCitation,
    ScoutReport,
    ClinicalConsensus,
    ExploratoryConsideration,
    ArbitratorSynthesis,
    Speculation,
    SpeculationStatus,
)


@pytest.fixture
def sample_patient_context():
    """Create a sample patient context for v2.1 tests."""
    return PatientContext(
        age=55,
        sex="male",
        comorbidities=["diabetes", "hypertension", "CKD"],
        current_medications=["metformin", "lisinopril", "amlodipine"],
        allergies=["penicillin"],
        failed_treatments=["sulfonylurea"],
        relevant_history="Previous MI 2 years ago",
        constraints=["cost sensitive"],
    )


@pytest.fixture
def sample_routing_decision():
    """Create a sample routing decision."""
    return RoutingDecision(
        mode=ConferenceMode.COMPLEX_DILEMMA,
        active_agents=[
            "empiricist", "skeptic", "pragmatist", 
            "patient_voice", "mechanist", "speculator"
        ],
        activate_scout=True,
        risk_profile=0.5,
        routing_rationale="Complex case with multiple comorbidities",
        complexity_signals_detected=["comorbidities:3", "failed_treatments:1"],
    )


@pytest.fixture
def sample_scout_citation():
    """Create a sample Scout citation."""
    return ScoutCitation(
        title="Meta-analysis of SGLT2 inhibitors in diabetic kidney disease",
        authors=["Smith J", "Jones A", "Brown K"],
        journal="NEJM",
        year=2024,
        pmid="12345678",
        evidence_grade=EvidenceGrade.META_ANALYSIS,
        sample_size=15000,
        relevance_score=0.95,
        key_finding="SGLT2 inhibitors reduce progression of CKD by 30%",
    )


@pytest.fixture
def sample_scout_report(sample_scout_citation):
    """Create a sample Scout report."""
    return ScoutReport(
        is_empty=False,
        query_keywords=["diabetes", "CKD", "treatment"],
        meta_analyses=[sample_scout_citation],
        high_quality_rcts=[
            ScoutCitation(
                title="RCT of empagliflozin in CKD",
                authors=["Lee M"],
                journal="Lancet",
                year=2024,
                evidence_grade=EvidenceGrade.RCT_LARGE,
                sample_size=6000,
                key_finding="Renal protection confirmed",
            )
        ],
        total_results_found=25,
        results_after_filtering=5,
    )


@pytest.fixture
def sample_clinical_consensus():
    """Create a sample clinical consensus."""
    return ClinicalConsensus(
        recommendation="Recommend SGLT2 inhibitor (empagliflozin) as add-on therapy",
        evidence_basis=[
            "EMPA-KIDNEY trial (PMID: 12345678)",
            "ADA/KDIGO Guidelines 2024",
        ],
        confidence=0.85,
        safety_profile="Generally well-tolerated; monitor for DKA, UTI",
        contraindications=["GFR < 20 mL/min", "Type 1 diabetes"],
        monitoring_required=["eGFR at 3 months", "Watch for volume depletion"],
    )


@pytest.fixture
def sample_exploratory_consideration():
    """Create a sample exploratory consideration."""
    return ExploratoryConsideration(
        hypothesis="GLP-1/GIP dual agonist may provide additional renal benefit",
        mechanism="Dual incretin pathway activation reduces inflammation",
        evidence_level="early_clinical",
        potential_benefit="Synergistic cardio-renal protection",
        risks=["Limited long-term safety data", "GI side effects"],
        what_would_validate="Head-to-head RCT vs SGLT2i in CKD population",
    )


@pytest.fixture
def sample_arbitrator_synthesis(sample_clinical_consensus, sample_exploratory_consideration):
    """Create a sample arbitrator synthesis."""
    return ArbitratorSynthesis(
        clinical_consensus=sample_clinical_consensus,
        exploratory_considerations=[sample_exploratory_consideration],
        tensions=[],
        safety_concerns_raised=["Monitor for volume depletion with diuretic combo"],
        stagnation_concerns_raised=["Consider newer agents if standard fails"],
        what_would_change_mind="New evidence showing harm of SGLT2i in this population",
        preserved_dissent=[],
        overall_confidence=0.82,
        uncertainty_map={
            "efficacy": "agreed",
            "safety": "agreed",
            "optimal_agent": "contested",
        },
    )


@pytest.fixture
def sample_speculation():
    """Create a sample speculation for testing."""
    return Speculation(
        origin_conference_id="conf_test_123",
        origin_query="Treatment options for diabetic CKD",
        hypothesis="Finerenone + SGLT2i combination may provide additive benefit",
        mechanism="Dual MR antagonism + SGLT2 inhibition targets different pathways",
        source_agent="speculator",
        initial_confidence="medium",
        validation_criteria="RCT of combination vs monotherapy in DKD",
        evidence_needed="Randomized trial with renal endpoints",
        watch_keywords=["finerenone", "SGLT2", "combination", "diabetic kidney"],
        status=SpeculationStatus.WATCHING,
    )
