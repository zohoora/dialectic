"""Tests for the Scout (Live Literature Search) - v2.1."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.scout.scout import (
    extract_search_keywords,
    build_pubmed_query,
    grade_evidence,
    extract_sample_size,
    extract_key_finding,
    run_scout,
)
from src.models.v2_schemas import (
    EvidenceGrade,
    PatientContext,
    ScoutCitation,
    ScoutReport,
)


# =============================================================================
# KEYWORD EXTRACTION TESTS
# =============================================================================


class TestKeywordExtraction:
    """Tests for extract_search_keywords function."""

    def test_extracts_from_entities(self):
        """Test keyword extraction from pre-extracted entities."""
        entities = {
            "conditions": ["diabetes", "hypertension"],
            "drugs": ["metformin"],
        }
        keywords = extract_search_keywords(
            "Patient with diabetes on metformin",
            entities,
        )
        assert "diabetes" in keywords
        assert "metformin" in keywords

    def test_extracts_from_text_fallback(self):
        """Test keyword extraction from text when no entities."""
        keywords = extract_search_keywords(
            "Treatment for diabetic neuropathy",
            None,
        )
        # Should extract meaningful words
        assert "diabetic" in keywords or "neuropathy" in keywords

    def test_removes_stopwords(self):
        """Test that common stopwords are removed."""
        keywords = extract_search_keywords(
            "What is the best treatment for the patient with diabetes",
            None,
        )
        # Common words should be filtered
        assert "what" not in keywords
        assert "the" not in keywords
        assert "best" not in keywords
        assert "with" not in keywords

    def test_limits_keywords(self):
        """Test that keywords are limited to max 10."""
        long_query = " ".join([f"term{i}" for i in range(20)])
        keywords = extract_search_keywords(long_query, None)
        assert len(keywords) <= 10

    def test_deduplicates_keywords(self):
        """Test that duplicate keywords are removed."""
        keywords = extract_search_keywords(
            "Diabetes diabetes DIABETES treatment",
            None,
        )
        lower_keywords = [k.lower() for k in keywords]
        # Should only have one instance of diabetes
        assert lower_keywords.count("diabetes") == 1


# =============================================================================
# PUBMED QUERY BUILDING TESTS
# =============================================================================


class TestPubMedQueryBuilding:
    """Tests for build_pubmed_query function."""

    def test_builds_valid_query(self):
        """Test that a valid PubMed query is built."""
        query = build_pubmed_query(["diabetes", "metformin"], 12)
        assert "diabetes" in query
        assert "metformin" in query
        assert "[Title/Abstract]" in query
        assert "[Date - Publication]" in query

    def test_includes_date_range(self):
        """Test that date range is included in query."""
        query = build_pubmed_query(["test"], 6)
        # Should contain date filter
        assert "Date" in query

    def test_limits_keywords_in_query(self):
        """Test that only first 5 keywords are used."""
        keywords = ["a", "b", "c", "d", "e", "f", "g"]
        query = build_pubmed_query(keywords, 12)
        # Only first 5 should be in query
        assert "f" not in query or "[Title/Abstract]" not in query.split("f")[1]


# =============================================================================
# EVIDENCE GRADING TESTS
# =============================================================================


class TestEvidenceGrading:
    """Tests for grade_evidence function."""

    def test_grades_meta_analysis(self):
        """Test grading of meta-analysis."""
        grade = grade_evidence(
            title="A meta-analysis of treatment outcomes",
            abstract="This systematic review...",
            journal="Cochrane Database",
            sample_size=None,
            is_preprint=False,
        )
        assert grade == EvidenceGrade.META_ANALYSIS

    def test_grades_systematic_review(self):
        """Test grading of systematic review."""
        grade = grade_evidence(
            title="Systematic review of interventions",
            abstract="We conducted a comprehensive review...",
            journal="Some Journal",
            sample_size=None,
            is_preprint=False,
        )
        assert grade == EvidenceGrade.META_ANALYSIS

    def test_grades_large_rct(self):
        """Test grading of large RCT (n > 100)."""
        grade = grade_evidence(
            title="A randomized controlled trial of treatment X",
            abstract="We conducted a double-blind RCT...",
            journal="NEJM",
            sample_size=500,
            is_preprint=False,
        )
        assert grade == EvidenceGrade.RCT_LARGE

    def test_grades_small_rct(self):
        """Test grading of small RCT (n < 100)."""
        grade = grade_evidence(
            title="Randomized trial of treatment Y",
            abstract="A controlled trial with 50 participants...",
            journal="Some Journal",
            sample_size=50,
            is_preprint=False,
        )
        assert grade == EvidenceGrade.RCT_SMALL

    def test_grades_preprint(self):
        """Test that preprints are graded appropriately."""
        grade = grade_evidence(
            title="Novel findings in treatment Z",
            abstract="Our RCT showed...",
            journal="medRxiv",
            sample_size=200,
            is_preprint=True,
        )
        assert grade == EvidenceGrade.PREPRINT

    def test_grades_case_report(self):
        """Test grading of case report."""
        grade = grade_evidence(
            title="Case report: unusual presentation",
            abstract="We present a case of...",
            journal="BMJ Case Reports",
            sample_size=None,
            is_preprint=False,
        )
        assert grade == EvidenceGrade.CASE_REPORT

    def test_grades_observational(self):
        """Test grading of observational study."""
        grade = grade_evidence(
            title="Cohort study of outcomes",
            abstract="A retrospective cohort analysis...",
            journal="Some Journal",
            sample_size=None,
            is_preprint=False,
        )
        assert grade == EvidenceGrade.OBSERVATIONAL


# =============================================================================
# SAMPLE SIZE EXTRACTION TESTS
# =============================================================================


class TestSampleSizeExtraction:
    """Tests for extract_sample_size function."""

    def test_extracts_n_equals_format(self):
        """Test extraction of n=X format."""
        size = extract_sample_size("We enrolled n=150 patients")
        assert size == 150

    def test_extracts_patients_format(self):
        """Test extraction of 'X patients' format."""
        size = extract_sample_size("A total of 200 patients were included")
        assert size == 200

    def test_extracts_participants_format(self):
        """Test extraction of 'X participants' format."""
        size = extract_sample_size("The study included 75 participants")
        assert size == 75

    def test_returns_none_for_no_size(self):
        """Test that None is returned when no size found."""
        size = extract_sample_size("This study examined treatment outcomes")
        assert size is None

    def test_handles_empty_abstract(self):
        """Test handling of empty abstract."""
        size = extract_sample_size("")
        assert size is None

    def test_handles_none_abstract(self):
        """Test handling of None abstract."""
        size = extract_sample_size(None)
        assert size is None


# =============================================================================
# KEY FINDING EXTRACTION TESTS
# =============================================================================


class TestKeyFindingExtraction:
    """Tests for extract_key_finding function."""

    def test_extracts_conclusion(self):
        """Test extraction from conclusion section."""
        finding = extract_key_finding(
            "Methods: We studied X. Results: Y happened. Conclusion: Treatment A is effective."
        )
        assert "effective" in finding.lower() or "treatment" in finding.lower()

    def test_extracts_results_show(self):
        """Test extraction from 'results show' statement."""
        finding = extract_key_finding(
            "Our results show that treatment B reduces pain by 50%"
        )
        assert "50%" in finding or "reduce" in finding.lower()

    def test_fallback_to_first_sentence(self):
        """Test fallback to first sentence when no conclusion."""
        finding = extract_key_finding(
            "This study examines outcomes. Additional details follow."
        )
        assert "study" in finding.lower() or "outcomes" in finding.lower()

    def test_handles_empty_abstract(self):
        """Test handling of empty abstract."""
        finding = extract_key_finding("")
        assert "available" in finding.lower() or finding == ""


# =============================================================================
# SCOUT REPORT TESTS
# =============================================================================


class TestScoutReport:
    """Tests for ScoutReport model and methods."""

    def test_empty_report_context_block(self):
        """Test context block for empty report."""
        report = ScoutReport(
            is_empty=True,
            query_keywords=["test"],
        )
        block = report.to_context_block()
        assert "NO RECENT EVIDENCE" in block

    def test_report_context_block_with_findings(self):
        """Test context block with findings."""
        report = ScoutReport(
            is_empty=False,
            query_keywords=["diabetes"],
            meta_analyses=[
                ScoutCitation(
                    title="Meta-analysis of diabetes treatments",
                    authors=["Smith J"],
                    year=2024,
                    evidence_grade=EvidenceGrade.META_ANALYSIS,
                    key_finding="Treatment X is effective",
                    pmid="12345678",
                )
            ],
            high_quality_rcts=[
                ScoutCitation(
                    title="RCT of new treatment",
                    authors=["Jones A"],
                    year=2024,
                    evidence_grade=EvidenceGrade.RCT_LARGE,
                    key_finding="Significant improvement observed",
                    sample_size=500,
                )
            ],
        )
        block = report.to_context_block()
        
        # Should include sections
        assert "Meta-Analyses" in block or "HIGHEST WEIGHT" in block
        assert "RCT" in block
        assert "12345678" in block  # PMID
        assert "Treatment X" in block


# =============================================================================
# FULL SCOUT INTEGRATION TESTS
# =============================================================================


class TestRunScout:
    """Integration tests for run_scout function."""

    @pytest.fixture
    def mock_pubmed_results(self):
        """Create mock PubMed search results."""
        return [
            {
                "title": "Meta-analysis of treatment outcomes",
                "authors": ["Smith J", "Jones A"],
                "journal": "Cochrane Database",
                "year": 2024,
                "pmid": "12345678",
                "abstract": "Conclusion: Treatment is effective. n=500 patients.",
            },
            {
                "title": "Randomized controlled trial",
                "authors": ["Brown K"],
                "journal": "NEJM",
                "year": 2024,
                "pmid": "23456789",
                "abstract": "This RCT included 200 patients. Results show efficacy.",
            },
            {
                "title": "Case report of unusual response",
                "authors": ["Lee M"],
                "journal": "BMJ Case Reports",
                "year": 2024,
                "pmid": "34567890",
                "abstract": "We present a case of adverse reaction.",
            },
        ]

    @pytest.mark.asyncio
    async def test_run_scout_returns_report(self, mock_pubmed_results):
        """Test that run_scout returns a ScoutReport."""
        with patch("src.scout.scout.PubMedClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.search = AsyncMock(return_value=mock_pubmed_results)
            
            report = await run_scout(
                query="What is the treatment for diabetes?",
                patient_context=None,
                date_range_months=12,
            )
            
            assert isinstance(report, ScoutReport)
            assert report.query_keywords is not None

    @pytest.mark.asyncio
    async def test_run_scout_categorizes_evidence(self, mock_pubmed_results):
        """Test that Scout categorizes evidence by grade."""
        with patch("src.scout.scout.PubMedClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.search = AsyncMock(return_value=mock_pubmed_results)
            
            report = await run_scout(
                query="Treatment for condition",
                patient_context=None,
                date_range_months=12,
            )
            
            # Should have categorized the results
            total = (
                len(report.meta_analyses) +
                len(report.high_quality_rcts) +
                len(report.preliminary_evidence) +
                len(report.conflicting_evidence)
            )
            assert total > 0 or report.is_empty

    @pytest.mark.asyncio
    async def test_run_scout_empty_results(self):
        """Test Scout with no results."""
        with patch("src.scout.scout.PubMedClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.search = AsyncMock(return_value=[])
            
            report = await run_scout(
                query="Very specific rare condition",
                patient_context=None,
                date_range_months=12,
            )
            
            assert report.is_empty is True

