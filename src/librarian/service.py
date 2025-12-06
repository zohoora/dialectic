"""
Librarian Service - Document analysis and query answering.

The Librarian is a specialized non-deliberating agent that analyzes uploaded
documents and provides information to other agents during deliberation.
"""

import logging
import re
from typing import Optional

from src.models.librarian import (
    FileManifestEntry,
    LibrarianConfig,
    LibrarianContext,
    LibrarianFile,
    LibrarianQuery,
    LibrarianSummary,
)
from src.utils.protocols import LLMClientProtocol


logger = logging.getLogger(__name__)


# System prompt for the Librarian
LIBRARIAN_SYSTEM_PROMPT = """You are the Librarian, a specialized document analysis agent supporting a multi-disciplinary medical case conference.

Your role is to:
1. Analyze uploaded documents (medical records, lab results, imaging reports, research papers)
2. Extract and summarize key clinical information relevant to the case query
3. Answer specific questions from other agents about document contents

Guidelines:
- Be precise and cite specific sections/pages when referencing documents
- Distinguish between facts from documents vs. your interpretations
- If information is unclear or missing in documents, state so explicitly
- Organize information logically (e.g., timeline, by document type, by relevance)
- Prioritize clinically significant findings
- Note any discrepancies between documents"""

SUMMARY_PROMPT_TEMPLATE = """Analyze the uploaded documents in the context of this clinical query:

**Query:** {query}

Provide a comprehensive summary that includes:

1. **Document Overview**: Brief description of each document type and its source
2. **Key Clinical Findings**: Most relevant information for the query
3. **Timeline** (if applicable): Chronological sequence of events/findings
4. **Critical Values/Alerts**: Any abnormal or concerning findings
5. **Gaps in Information**: What's missing that would be helpful for the case

Format your response as:

## Document Manifest
[List each document with brief description]

## Key Findings
[Bullet points of most relevant findings for the query]

## Summary
[2-3 paragraph synthesis of the documents relevant to the query]

## Information Gaps
[What additional information would be helpful]"""

QUERY_PROMPT_TEMPLATE = """Based on the uploaded documents, answer this question from one of the conference agents:

**Question:** {question}

Guidelines:
- Answer based ONLY on information in the uploaded documents
- Cite specific documents/sections when possible
- If the information is not in the documents, say so clearly
- Be concise but thorough"""


class LibrarianService:
    """
    Service for document analysis and query answering.
    
    Manages the Librarian context for a conference, including:
    - Initial document analysis and summary generation
    - Answering agent queries during deliberation
    - Tracking query limits per agent per round
    """
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        config: Optional[LibrarianConfig] = None,
    ):
        """
        Initialize the Librarian service.
        
        Args:
            llm_client: LLM client for API calls (must support multimodal)
            config: Librarian configuration (uses defaults if not provided)
        """
        self.llm_client = llm_client
        self.config = config or LibrarianConfig()
        self.context: Optional[LibrarianContext] = None
    
    async def initialize(
        self,
        files: list[LibrarianFile],
        query: str,
    ) -> LibrarianSummary:
        """
        Initialize the Librarian with files and generate initial summary.
        
        This should be called before the conference starts. It analyzes all
        uploaded files and generates a contextual summary for the agents.
        
        Args:
            files: List of files to analyze
            query: The clinical query for context
        
        Returns:
            LibrarianSummary with document analysis
        """
        if not files:
            # No files - return empty summary
            return LibrarianSummary(
                summary="No documents were provided for analysis.",
                file_manifest=[],
                key_findings=[],
                relevant_to_query=False,
            )
        
        # Create context
        self.context = LibrarianContext(
            config=self.config,
            files=files,
        )
        
        # Build file list for API call
        file_tuples = [
            (f.content, f.mime_type) for f in files
        ]
        
        # Generate summary
        messages = [
            {"role": "system", "content": LIBRARIAN_SYSTEM_PROMPT},
            {"role": "user", "content": SUMMARY_PROMPT_TEMPLATE.format(query=query)},
        ]
        
        logger.info(f"Librarian analyzing {len(files)} files for query")
        
        response = await self.llm_client.complete_multimodal(
            model=self.config.model,
            messages=messages,
            files=file_tuples,
            temperature=self.config.temperature,
        )
        
        # Build summary
        summary = LibrarianSummary(
            summary=response.content,
            file_manifest=[
                FileManifestEntry(
                    filename=f.filename,
                    file_type=f.file_type,
                    size_bytes=f.size_bytes,
                )
                for f in files
            ],
            key_findings=self._extract_key_findings(response.content),
            relevant_to_query=True,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        
        self.context.summary = summary
        logger.info(f"Librarian summary generated: {response.input_tokens} input, {response.output_tokens} output tokens")
        
        return summary
    
    async def answer_query(
        self,
        agent_id: str,
        question: str,
        round_number: int,
    ) -> Optional[LibrarianQuery]:
        """
        Answer a query from an agent about the documents.
        
        Respects rate limits (max_queries_per_turn per agent per round).
        
        Args:
            agent_id: ID of the agent asking
            question: The question about document contents
            round_number: Current conference round
        
        Returns:
            LibrarianQuery with response, or None if rate limited or no context
        """
        if self.context is None:
            logger.warning(f"Agent {agent_id} tried to query Librarian before initialization")
            return None
        
        if not self.context.files:
            # No files to query
            return LibrarianQuery(
                agent_id=agent_id,
                question=question,
                response="No documents were provided for this conference.",
                round_number=round_number,
            )
        
        # Check rate limit
        if not self.context.can_query(agent_id, round_number):
            queries_remaining = self.context.get_queries_remaining(agent_id, round_number)
            logger.info(f"Agent {agent_id} rate limited: {queries_remaining} queries remaining")
            return None
        
        # Build message with files
        file_tuples = [
            (f.content, f.mime_type) for f in self.context.files
        ]
        
        messages = [
            {"role": "system", "content": LIBRARIAN_SYSTEM_PROMPT},
            {"role": "user", "content": QUERY_PROMPT_TEMPLATE.format(question=question)},
        ]
        
        logger.info(f"Librarian answering query from {agent_id}: {question[:50]}...")
        
        response = await self.llm_client.complete_multimodal(
            model=self.config.model,
            messages=messages,
            files=file_tuples,
            temperature=self.config.temperature,
        )
        
        # Create query record
        query = LibrarianQuery(
            agent_id=agent_id,
            question=question,
            response=response.content,
            round_number=round_number,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        
        # Add to context
        self.context.add_query(query)
        
        logger.info(f"Librarian answered query: {response.input_tokens} input, {response.output_tokens} output tokens")
        
        return query
    
    def get_summary_for_agents(self) -> str:
        """
        Get the summary text to inject into agent prompts.
        
        This is the text that gets prepended to the query for all agents
        in Round 1 (and optionally later rounds).
        
        Returns:
            Formatted summary string, or empty string if no summary
        """
        if self.context is None or self.context.summary is None:
            return ""
        
        summary = self.context.summary
        
        # Build manifest section
        manifest_lines = []
        for entry in summary.file_manifest:
            size_kb = entry.size_bytes / 1024
            manifest_lines.append(f"- **{entry.filename}** ({entry.file_type.value}, {size_kb:.1f} KB)")
        
        manifest_section = "\n".join(manifest_lines) if manifest_lines else "No documents"
        
        return f"""---
## 📚 Document Context (from Librarian)

### Uploaded Documents
{manifest_section}

### Summary
{summary.summary}

---
"""
    
    def get_queries_remaining(self, agent_id: str, round_number: int) -> int:
        """Get number of queries remaining for an agent this round."""
        if self.context is None:
            return 0
        return self.context.get_queries_remaining(agent_id, round_number)
    
    def get_total_token_usage(self) -> tuple[int, int]:
        """
        Get total token usage from the Librarian.
        
        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        if self.context is None:
            return (0, 0)
        return (self.context.total_input_tokens, self.context.total_output_tokens)
    
    def _extract_key_findings(self, summary_text: str) -> list[str]:
        """
        Extract key findings from the summary text.
        
        Looks for bullet points under "Key Findings" section.
        """
        findings = []
        
        # Look for Key Findings section
        lines = summary_text.split("\n")
        in_findings_section = False
        
        for line in lines:
            line = line.strip()
            
            if "key findings" in line.lower():
                in_findings_section = True
                continue
            
            if in_findings_section:
                # Check if we hit another section header
                if line.startswith("##") or line.startswith("**") and line.endswith("**"):
                    if "findings" not in line.lower():
                        break
                
                # Extract bullet points
                if line.startswith("- ") or line.startswith("* "):
                    findings.append(line[2:].strip())
                elif line.startswith("• "):
                    findings.append(line[2:].strip())
        
        return findings[:10]  # Limit to 10 key findings
    
    @staticmethod
    def extract_queries_from_response(response_text: str) -> list[str]:
        """
        Extract librarian queries from an agent's response.
        
        Looks for patterns like [LIBRARIAN: question] in the response.
        
        Args:
            response_text: The agent's response text
        
        Returns:
            List of extracted questions
        """
        # Pattern matches [LIBRARIAN: question text]
        pattern = r'\[LIBRARIAN:\s*([^\]]+)\]'
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        return [q.strip() for q in matches if q.strip()]
    
    async def process_agent_queries(
        self,
        agent_id: str,
        response_text: str,
        round_number: int,
    ) -> list[LibrarianQuery]:
        """
        Extract and answer all librarian queries from an agent's response.
        
        Args:
            agent_id: ID of the agent
            response_text: The agent's response text containing queries
            round_number: Current conference round
        
        Returns:
            List of LibrarianQuery objects with questions and answers
        """
        queries = self.extract_queries_from_response(response_text)
        answered_queries = []
        
        for question in queries:
            # Check rate limit
            if not self.context or not self.context.can_query(agent_id, round_number):
                logger.info(f"Agent {agent_id} has reached query limit for round {round_number}")
                break
            
            query_result = await self.answer_query(
                agent_id=agent_id,
                question=question,
                round_number=round_number,
            )
            
            if query_result:
                answered_queries.append(query_result)
        
        return answered_queries
    
    @staticmethod
    def format_query_answers(queries: list[LibrarianQuery]) -> str:
        """
        Format librarian query answers for inclusion in the response.
        
        Args:
            queries: List of answered LibrarianQuery objects
        
        Returns:
            Formatted string with questions and answers
        """
        if not queries:
            return ""
        
        lines = ["\n---\n**📚 Librarian Responses:**\n"]
        for i, q in enumerate(queries, 1):
            lines.append(f"**Q{i}:** {q.question}")
            lines.append(f"**A{i}:** {q.response}\n")
        
        return "\n".join(lines)

