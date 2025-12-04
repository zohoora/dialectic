"""
Scout - Live Literature Search and Evidence Grading.

Fetches recent publications from PubMed, grades evidence quality,
and formats findings for injection into agent contexts.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from src.grounding.pubmed_client import PubMedClient
from src.models.v2_schemas import (
    ClassifiedQuery,
    EvidenceGrade,
    PatientContext,
    ScoutCitation,
    ScoutReport,
)


logger = logging.getLogger(__name__)


# =============================================================================
# KEYWORD EXTRACTION
# =============================================================================


def extract_search_keywords(
    query_text: str,
    extracted_entities: Optional[dict] = None,
) -> list[str]:
    """
    Extract meaningful search keywords from the query.
    
    Args:
        query_text: Raw query text
        extracted_entities: Optional pre-extracted entities from classifier
        
    Returns:
        List of search keywords (max 10)
    """
    keywords = []

    # Use pre-extracted entities if available
    if extracted_entities:
        if extracted_entities.get("conditions"):
            keywords.extend(extracted_entities["conditions"])
        if extracted_entities.get("drugs"):
            keywords.extend(extracted_entities["drugs"])
        if extracted_entities.get("symptoms"):
            keywords.extend(extracted_entities["symptoms"])
        if extracted_entities.get("procedures"):
            keywords.extend(extracted_entities["procedures"])

    # Fallback to text extraction if no entities
    if not keywords:
        # Medical stopwords to filter out
        stopwords = {
            "patient", "treatment", "therapy", "what", "how", "why",
            "best", "good", "should", "could", "would", "recommend",
            "options", "approach", "management", "help", "the", "for",
            "with", "and", "but", "this", "that", "have", "has", "been",
            "can", "will", "may", "might", "any", "some", "all",
            "are", "was", "were", "been", "being", "which", "when",
            "where", "who", "whom", "about", "into", "through", "during",
            "before", "after", "above", "below", "from", "down",
            "out", "off", "over", "under", "again", "further", "then",
            "once", "here", "there", "than", "too", "very", "just",
            "only", "own", "same", "other", "such", "more", "most",
        }

        # Extract words (3+ chars)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", query_text.lower())
        keywords = [w for w in words if w not in stopwords]

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)

    return unique_keywords[:10]  # Limit to top 10


def build_pubmed_query(
    keywords: list[str],
    date_range_months: int = 12,
) -> str:
    """
    Build a PubMed query string with date filtering.
    
    Args:
        keywords: Search keywords
        date_range_months: How far back to search (months)
        
    Returns:
        Formatted PubMed query string
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range_months * 30)

    date_filter = (
        f'("{start_date.strftime("%Y/%m/%d")}"[Date - Publication] : '
        f'"{end_date.strftime("%Y/%m/%d")}"[Date - Publication])'
    )

    # Build keyword query (OR for broader search)
    if len(keywords) <= 3:
        # For few keywords, use AND
        keyword_query = " AND ".join(
            [f'"{kw}"[Title/Abstract]' for kw in keywords]
        )
    else:
        # For many keywords, use primary + OR for others
        primary = keywords[:2]
        secondary = keywords[2:5]
        keyword_query = (
            " AND ".join([f'"{kw}"[Title/Abstract]' for kw in primary])
            + " AND ("
            + " OR ".join([f'"{kw}"[Title/Abstract]' for kw in secondary])
            + ")"
        )

    return f"({keyword_query}) AND {date_filter}"


# =============================================================================
# EVIDENCE GRADING
# =============================================================================


def grade_evidence(
    title: str,
    abstract: Optional[str],
    journal: Optional[str],
    sample_size: Optional[int],
    is_preprint: bool = False,
) -> EvidenceGrade:
    """
    Grade the evidence quality of a publication.
    
    Args:
        title: Article title
        abstract: Article abstract (if available)
        journal: Journal name
        sample_size: Sample size if extractable
        is_preprint: Whether this is a preprint
        
    Returns:
        EvidenceGrade enum value
    """
    title_lower = title.lower()
    abstract_lower = (abstract or "").lower()
    combined = f"{title_lower} {abstract_lower}"

    # Check for meta-analysis / systematic review
    meta_keywords = [
        "meta-analysis",
        "systematic review",
        "cochrane",
        "pooled analysis",
        "network meta-analysis",
    ]
    if any(kw in combined for kw in meta_keywords):
        return EvidenceGrade.META_ANALYSIS

    # Preprint check
    if is_preprint:
        return EvidenceGrade.PREPRINT

    # RCT detection
    rct_keywords = [
        "randomized",
        "randomised",
        "rct",
        "controlled trial",
        "double-blind",
        "placebo-controlled",
        "randomized controlled",
    ]
    is_rct = any(kw in combined for kw in rct_keywords)

    if is_rct:
        if sample_size and sample_size > 100:
            return EvidenceGrade.RCT_LARGE
        else:
            return EvidenceGrade.RCT_SMALL

    # Case report
    case_keywords = ["case report", "case series", "case presentation"]
    if any(kw in combined for kw in case_keywords):
        return EvidenceGrade.CASE_REPORT

    # Observational
    observational_keywords = [
        "cohort",
        "retrospective",
        "prospective",
        "observational",
        "registry",
        "cross-sectional",
        "longitudinal",
    ]
    if any(kw in combined for kw in observational_keywords):
        return EvidenceGrade.OBSERVATIONAL

    # Default to observational
    return EvidenceGrade.OBSERVATIONAL


def extract_sample_size(abstract: Optional[str]) -> Optional[int]:
    """
    Attempt to extract sample size from abstract.
    
    Args:
        abstract: Article abstract text
        
    Returns:
        Sample size if found, None otherwise
    """
    if not abstract:
        return None

    patterns = [
        r"n\s*=\s*(\d+)",
        r"(\d+)\s+patients",
        r"(\d+)\s+participants",
        r"(\d+)\s+subjects",
        r"(\d+)\s+individuals",
        r"sample\s+(?:size|of)\s+(\d+)",
        r"enrolled\s+(\d+)",
        r"included\s+(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, abstract.lower())
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue

    return None


def extract_key_finding(abstract: Optional[str]) -> str:
    """
    Extract the main finding from an abstract.
    
    Looks for conclusion sections or result statements.
    
    Args:
        abstract: Article abstract text
        
    Returns:
        Key finding summary (one sentence)
    """
    if not abstract:
        return "No abstract available"

    abstract_text = abstract.strip()

    # Try to find conclusion section
    conclusion_patterns = [
        r"(?:conclusion|conclusions)[:\s]+(.+?)(?:\.\s|$)",
        r"(?:in conclusion)[,\s]+(.+?)(?:\.\s|$)",
        r"(?:we conclude that)[,\s]+(.+?)(?:\.\s|$)",
        r"(?:these (?:results|findings) suggest)[,\s]+(.+?)(?:\.\s|$)",
        r"(?:our (?:results|findings) (?:indicate|suggest|show))[,\s]+(.+?)(?:\.\s|$)",
    ]

    for pattern in conclusion_patterns:
        match = re.search(pattern, abstract_text, re.IGNORECASE | re.DOTALL)
        if match:
            finding = match.group(1).strip()
            # Clean up and truncate
            finding = re.sub(r"\s+", " ", finding)
            if len(finding) > 200:
                finding = finding[:197] + "..."
            return finding[0].upper() + finding[1:] if finding else "Finding unclear"

    # Fallback: first sentence
    sentences = abstract_text.split(".")
    if sentences:
        first = sentences[0].strip()
        if len(first) > 200:
            first = first[:197] + "..."
        return first

    return "Finding unclear from abstract"


# =============================================================================
# MAIN SCOUT FUNCTION
# =============================================================================


async def run_scout(
    query: str,
    patient_context: Optional[PatientContext] = None,
    extracted_entities: Optional[dict] = None,
    date_range_months: int = 12,
    max_results: int = 20,
    pubmed_api_key: Optional[str] = None,
) -> ScoutReport:
    """
    Main Scout function. Fetches, grades, and organizes recent literature.
    
    Args:
        query: The clinical query text
        patient_context: Optional patient information
        extracted_entities: Optional pre-extracted entities
        date_range_months: How far back to search (default 12 months)
        max_results: Maximum PubMed results to fetch
        pubmed_api_key: Optional NCBI API key for higher rate limits
        
    Returns:
        ScoutReport with categorized evidence
    """
    # Extract keywords
    keywords = extract_search_keywords(query, extracted_entities)

    if not keywords:
        logger.warning("No keywords extracted from query")
        return ScoutReport(
            query_keywords=[],
            is_empty=True,
            date_range_months=date_range_months,
        )

    logger.info(f"Scout searching for: {keywords}")

    # Build PubMed query
    pubmed_query = build_pubmed_query(keywords, date_range_months)

    # Initialize PubMed client
    pubmed_client = PubMedClient(api_key=pubmed_api_key)

    # Search PubMed
    try:
        search_result = await pubmed_client.search(pubmed_query, max_results=max_results)

        if not search_result.found:
            logger.info("No PubMed results found")
            return ScoutReport(
                query_keywords=keywords,
                is_empty=True,
                date_range_months=date_range_months,
                search_queries_used=[pubmed_query],
            )

        # Fetch article details
        articles = await pubmed_client.fetch_multiple(search_result.pmids)

        if not articles:
            return ScoutReport(
                query_keywords=keywords,
                is_empty=True,
                date_range_months=date_range_months,
                search_queries_used=[pubmed_query],
                total_results_found=search_result.total_count,
            )

        logger.info(f"Scout found {len(articles)} articles")

    except Exception as e:
        logger.error(f"Scout PubMed search failed: {e}")
        return ScoutReport(
            query_keywords=keywords,
            is_empty=True,
            date_range_months=date_range_months,
            search_queries_used=[pubmed_query],
        )

    # Convert to ScoutCitations with grading
    citations = []
    for article in articles:
        sample_size = extract_sample_size(article.abstract)
        grade = grade_evidence(
            title=article.title,
            abstract=article.abstract,
            journal=article.journal,
            sample_size=sample_size,
            is_preprint=False,
        )

        citation = ScoutCitation(
            title=article.title,
            authors=article.authors,
            journal=article.journal,
            year=article.year,
            pmid=article.pmid,
            doi=article.doi,
            abstract=article.abstract,
            evidence_grade=grade,
            sample_size=sample_size,
            is_preprint=False,
            relevance_score=0.5,  # Could be improved with embedding similarity
            key_finding=extract_key_finding(article.abstract),
        )
        citations.append(citation)

    # Categorize by evidence grade
    meta_analyses = []
    high_quality_rcts = []
    preliminary = []
    conflicting = []

    for citation in citations:
        if citation.evidence_grade == EvidenceGrade.META_ANALYSIS:
            meta_analyses.append(citation)
        elif citation.evidence_grade in [EvidenceGrade.RCT_LARGE, EvidenceGrade.RCT_SMALL]:
            high_quality_rcts.append(citation)
        elif citation.conflicts_with_consensus:
            conflicting.append(citation)
        else:
            preliminary.append(citation)

    # Sort each category by year (most recent first)
    meta_analyses.sort(key=lambda x: x.year, reverse=True)
    high_quality_rcts.sort(key=lambda x: x.year, reverse=True)
    preliminary.sort(key=lambda x: x.year, reverse=True)

    # Limit to top results per category
    return ScoutReport(
        query_keywords=keywords,
        date_range_months=date_range_months,
        meta_analyses=meta_analyses[:3],
        high_quality_rcts=high_quality_rcts[:5],
        preliminary_evidence=preliminary[:5],
        conflicting_evidence=conflicting[:3],
        total_results_found=search_result.total_count,
        results_after_filtering=len(citations),
        is_empty=False,
        search_queries_used=[pubmed_query],
    )

