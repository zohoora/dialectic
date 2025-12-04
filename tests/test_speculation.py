"""Tests for the Speculation Library and Validator (v2.1)."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.speculation.library import SpeculationLibrary
from src.speculation.validator import SpeculationValidator, run_validation_scan
from src.models.v2_schemas import (
    EvidenceGrade,
    ScoutCitation,
    ScoutReport,
    Speculation,
    SpeculationStatus,
    ValidationResult,
    WatchListTrigger,
)


# =============================================================================
# SPECULATION LIBRARY TESTS
# =============================================================================


class TestSpeculationLibrary:
    """Tests for SpeculationLibrary class."""

    @pytest.fixture
    def library(self, tmp_path):
        """Create a SpeculationLibrary with temp storage."""
        storage_path = tmp_path / "speculations.json"
        return SpeculationLibrary(storage_path=storage_path)

    @pytest.fixture
    def sample_speculation(self):
        """Create a sample speculation."""
        return Speculation(
            origin_conference_id="conf_123",
            origin_query="Treatment for refractory pain",
            hypothesis="Low-dose naltrexone may modulate glial cells",
            mechanism="LDN antagonizes TLR4 receptors on microglia",
            source_agent="speculator",
            initial_confidence="low",
            validation_criteria="RCT showing pain reduction vs placebo",
            watch_keywords=["low-dose naltrexone", "LDN", "glial", "TLR4"],
        )

    def test_store_speculation(self, library, sample_speculation):
        """Test storing a new speculation."""
        spec_id = library.store(sample_speculation)
        
        assert spec_id is not None
        assert spec_id == sample_speculation.speculation_id
        
        # Verify it's stored
        retrieved = library.get(spec_id)
        assert retrieved is not None
        assert retrieved.hypothesis == sample_speculation.hypothesis

    def test_store_sets_watching_status(self, library, sample_speculation):
        """Test that storing sets status to WATCHING if keywords provided."""
        library.store(sample_speculation)
        
        retrieved = library.get(sample_speculation.speculation_id)
        assert retrieved.status == SpeculationStatus.WATCHING

    def test_get_nonexistent(self, library):
        """Test getting a nonexistent speculation."""
        result = library.get("nonexistent_id")
        assert result is None

    def test_remove_speculation(self, library, sample_speculation):
        """Test removing a speculation."""
        library.store(sample_speculation)
        
        # Verify stored
        assert library.get(sample_speculation.speculation_id) is not None
        
        # Remove
        result = library.remove(sample_speculation.speculation_id)
        assert result is True
        
        # Verify removed
        assert library.get(sample_speculation.speculation_id) is None

    def test_remove_nonexistent(self, library):
        """Test removing a nonexistent speculation."""
        result = library.remove("nonexistent_id")
        assert result is False

    def test_update_status(self, library, sample_speculation):
        """Test updating speculation status."""
        library.store(sample_speculation)
        
        result = library.update_status(
            sample_speculation.speculation_id,
            SpeculationStatus.PARTIALLY_VALIDATED,
        )
        
        assert result is True
        
        retrieved = library.get(sample_speculation.speculation_id)
        assert retrieved.status == SpeculationStatus.PARTIALLY_VALIDATED

    def test_search_relevant(self, library, sample_speculation):
        """Test searching for relevant speculations."""
        library.store(sample_speculation)
        
        results = library.search_relevant(
            "Patient with chronic pain considering naltrexone",
            max_results=5,
        )
        
        # Should find our speculation due to keyword match
        assert len(results) > 0
        assert any(s.speculation_id == sample_speculation.speculation_id for s in results)

    def test_search_relevant_filters_by_status(self, library, sample_speculation):
        """Test that search filters by status."""
        library.store(sample_speculation)
        
        # Change status to CONTRADICTED
        library.update_status(
            sample_speculation.speculation_id,
            SpeculationStatus.CONTRADICTED,
        )
        
        # Search should not find it (CONTRADICTED is not active)
        results = library.search_relevant(
            "naltrexone treatment",
            max_results=5,
        )
        
        assert len(results) == 0

    def test_get_all_watch_keywords(self, library, sample_speculation):
        """Test getting all watch keywords."""
        library.store(sample_speculation)
        
        keywords = library.get_all_watch_keywords()
        
        assert len(keywords) > 0
        assert any(
            sample_speculation.speculation_id == entry["speculation_id"]
            for entry in keywords
        )

    def test_record_evidence_match(self, library, sample_speculation):
        """Test recording evidence match."""
        library.store(sample_speculation)
        
        citations = [
            ScoutCitation(
                title="LDN for chronic pain",
                authors=["Smith J"],
                year=2024,
                evidence_grade=EvidenceGrade.RCT_SMALL,
                key_finding="Significant pain reduction",
            )
        ]
        
        trigger = library.record_evidence_match(
            sample_speculation.speculation_id,
            citations,
            match_quality="partial",
        )
        
        assert isinstance(trigger, WatchListTrigger)
        assert trigger.speculation_id == sample_speculation.speculation_id
        
        # Check status updated
        retrieved = library.get(sample_speculation.speculation_id)
        assert retrieved.status == SpeculationStatus.EVIDENCE_FOUND

    def test_get_pending_triggers(self, library, sample_speculation):
        """Test getting pending triggers."""
        library.store(sample_speculation)
        
        citations = [
            ScoutCitation(
                title="New LDN study",
                authors=["Jones A"],
                year=2024,
                evidence_grade=EvidenceGrade.OBSERVATIONAL,
                key_finding="Promising results",
            )
        ]
        
        library.record_evidence_match(
            sample_speculation.speculation_id,
            citations,
        )
        
        pending = library.get_pending_triggers()
        assert len(pending) > 0
        assert all(t.requires_human_review for t in pending)

    def test_promote_to_experience_library(self, library, sample_speculation):
        """Test promoting speculation to experience library."""
        library.store(sample_speculation)
        
        result = library.promote_to_experience_library(
            sample_speculation.speculation_id,
            "exp_123",
        )
        
        assert result is True
        
        retrieved = library.get(sample_speculation.speculation_id)
        assert retrieved.status == SpeculationStatus.VALIDATED
        assert retrieved.promoted_to_experience_library is True
        assert retrieved.experience_library_id == "exp_123"

    def test_get_stats(self, library, sample_speculation):
        """Test getting library statistics."""
        library.store(sample_speculation)
        
        stats = library.get_stats()
        
        assert "total_speculations" in stats
        assert stats["total_speculations"] == 1
        assert "status_counts" in stats

    def test_extract_speculation_from_response(self, library):
        """Test extracting speculation from agent response."""
        response = """
        Based on the mechanism, I propose:
        
        **HYPOTHESIS: Low-dose naltrexone for neuropathic pain**
        
        Proposed mechanism: LDN blocks TLR4 on glial cells
        
        Evidence that would validate: RCT showing efficacy
        
        Risk/Reward: Low risk / Moderate potential benefit
        """
        
        speculation = library.extract_speculation_from_response(
            response_content=response,
            conference_id="conf_123",
            query="Treatment for neuropathic pain",
        )
        
        assert speculation is not None
        assert "naltrexone" in speculation.hypothesis.lower()

    def test_persistence(self, tmp_path, sample_speculation):
        """Test that library persists to disk."""
        storage_path = tmp_path / "test_speculations.json"
        
        # Create library and store
        library1 = SpeculationLibrary(storage_path=storage_path)
        library1.store(sample_speculation)
        
        # Create new library instance pointing to same file
        library2 = SpeculationLibrary(storage_path=storage_path)
        
        # Should load persisted data
        retrieved = library2.get(sample_speculation.speculation_id)
        assert retrieved is not None
        assert retrieved.hypothesis == sample_speculation.hypothesis


# =============================================================================
# SPECULATION VALIDATOR TESTS
# =============================================================================


class TestSpeculationValidator:
    """Tests for SpeculationValidator class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def validator(self, mock_llm_client):
        """Create a SpeculationValidator."""
        return SpeculationValidator(mock_llm_client)

    @pytest.fixture
    def sample_speculation(self):
        """Create a sample speculation for testing."""
        return Speculation(
            origin_conference_id="conf_123",
            origin_query="Treatment for condition X",
            hypothesis="Drug Y may help condition X",
            mechanism="Drug Y blocks receptor Z",
            validation_criteria="RCT showing improvement",
            watch_keywords=["Drug Y", "condition X"],
        )

    @pytest.fixture
    def confirming_evidence(self):
        """Create evidence that confirms a hypothesis."""
        return [
            ScoutCitation(
                title="Meta-analysis of Drug Y for condition X",
                authors=["Smith J"],
                year=2024,
                evidence_grade=EvidenceGrade.META_ANALYSIS,
                key_finding="Drug Y significantly improves condition X outcomes",
                sample_size=1000,
            )
        ]

    @pytest.fixture
    def weak_evidence(self):
        """Create weak/preliminary evidence."""
        return [
            ScoutCitation(
                title="Case report of Drug Y use",
                authors=["Jones A"],
                year=2024,
                evidence_grade=EvidenceGrade.CASE_REPORT,
                key_finding="Patient improved on Drug Y",
            )
        ]

    @pytest.mark.asyncio
    async def test_validate_no_evidence(self, validator, sample_speculation):
        """Test validation with no evidence."""
        result = await validator.validate(sample_speculation, [])
        
        assert result.support_level == "inconclusive"
        assert result.action == "keep_watching"
        assert result.new_status == SpeculationStatus.WATCHING

    @pytest.mark.asyncio
    async def test_validate_confirming_evidence(
        self, validator, sample_speculation, confirming_evidence, mock_llm_client
    ):
        """Test validation with confirming high-quality evidence."""
        # Mock LLM to return confirming assessment
        mock_llm_client.complete = AsyncMock(return_value=MagicMock(
            content="""
            SUPPORT_LEVEL: confirms
            
            KEY_FINDINGS:
            - Meta-analysis shows significant improvement
            
            REASONING:
            The meta-analysis provides strong support for the hypothesis.
            """
        ))
        
        result = await validator.validate(
            sample_speculation,
            confirming_evidence,
        )
        
        assert result.support_level == "confirms"
        assert result.evidence_quality == EvidenceGrade.META_ANALYSIS
        # High quality + confirms should trigger promotion
        assert result.action == "promote_to_experience_library"
        assert result.new_status == SpeculationStatus.VALIDATED
        assert result.requires_human_review is True

    @pytest.mark.asyncio
    async def test_validate_partial_support(
        self, validator, sample_speculation, weak_evidence, mock_llm_client
    ):
        """Test validation with partial/weak support."""
        mock_llm_client.complete = AsyncMock(return_value=MagicMock(
            content="""
            SUPPORT_LEVEL: partially_supports
            
            REASONING:
            Case report provides some support but needs more evidence.
            """
        ))
        
        result = await validator.validate(
            sample_speculation,
            weak_evidence,
        )
        
        assert result.support_level == "partially_supports"
        assert result.action == "upgrade_status"
        assert result.new_status == SpeculationStatus.PARTIALLY_VALIDATED

    @pytest.mark.asyncio
    async def test_validate_contradicting_evidence(
        self, validator, sample_speculation, mock_llm_client
    ):
        """Test validation with contradicting evidence."""
        contradicting = [
            ScoutCitation(
                title="RCT shows Drug Y ineffective for condition X",
                authors=["Brown K"],
                year=2024,
                evidence_grade=EvidenceGrade.RCT_LARGE,
                key_finding="No significant difference from placebo",
                sample_size=500,
            )
        ]
        
        mock_llm_client.complete = AsyncMock(return_value=MagicMock(
            content="""
            SUPPORT_LEVEL: contradicts
            
            REASONING:
            Large RCT shows Drug Y is not effective for this condition.
            """
        ))
        
        result = await validator.validate(
            sample_speculation,
            contradicting,
        )
        
        assert result.support_level == "contradicts"
        assert result.action == "deprecate"
        assert result.new_status == SpeculationStatus.CONTRADICTED
        assert result.requires_human_review is True


# =============================================================================
# VALIDATION SCAN TESTS
# =============================================================================


class TestValidationScan:
    """Tests for run_validation_scan function."""

    @pytest.fixture
    def library_with_speculations(self, tmp_path):
        """Create library with speculations."""
        library = SpeculationLibrary(tmp_path / "test.json")
        
        # Add speculation with watch keywords
        spec = Speculation(
            origin_conference_id="conf_123",
            origin_query="Test query",
            hypothesis="Test hypothesis about Drug X",
            mechanism="Test mechanism",
            watch_keywords=["Drug X", "condition Y"],
            status=SpeculationStatus.WATCHING,
        )
        library.store(spec)
        
        return library

    @pytest.fixture
    def scout_report_with_match(self):
        """Create Scout report that matches watch keywords."""
        return ScoutReport(
            is_empty=False,
            query_keywords=["Drug X"],
            high_quality_rcts=[
                ScoutCitation(
                    title="New study of Drug X for condition Y",
                    authors=["Smith J"],
                    year=2024,
                    evidence_grade=EvidenceGrade.RCT_LARGE,
                    key_finding="Drug X shows efficacy",
                    sample_size=200,
                )
            ],
        )

    @pytest.mark.asyncio
    async def test_scan_finds_matches(
        self, library_with_speculations, scout_report_with_match
    ):
        """Test that validation scan finds matches."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value=MagicMock(
            content="SUPPORT_LEVEL: partially_supports\nREASONING: Related evidence found"
        ))
        validator = SpeculationValidator(mock_llm)
        
        results = await run_validation_scan(
            library_with_speculations,
            scout_report_with_match,
            validator,
        )
        
        # Should find the matching speculation
        assert len(results) > 0
        assert all(isinstance(r, ValidationResult) for r in results)

    @pytest.mark.asyncio
    async def test_scan_empty_report(self, library_with_speculations):
        """Test validation scan with empty Scout report."""
        empty_report = ScoutReport(is_empty=True, query_keywords=[])
        validator = SpeculationValidator(MagicMock())
        
        results = await run_validation_scan(
            library_with_speculations,
            empty_report,
            validator,
        )
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_scan_no_matching_keywords(self, library_with_speculations):
        """Test validation scan when no keywords match."""
        non_matching_report = ScoutReport(
            is_empty=False,
            query_keywords=["unrelated"],
            high_quality_rcts=[
                ScoutCitation(
                    title="Study about something else entirely",
                    authors=["Other A"],
                    year=2024,
                    evidence_grade=EvidenceGrade.RCT_LARGE,
                    key_finding="Unrelated finding",
                )
            ],
        )
        validator = SpeculationValidator(MagicMock())
        
        results = await run_validation_scan(
            library_with_speculations,
            non_matching_report,
            validator,
        )
        
        # No matches expected
        assert len(results) == 0

