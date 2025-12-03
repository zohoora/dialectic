"""
Async conference runner service.

This module provides the main async function for running AI case conferences.
"""

from typing import Optional

from src.conference.engine import ConferenceEngine, ProgressStage, ProgressUpdate
from src.grounding.engine import GroundingEngine
from src.librarian.service import LibrarianService
from src.llm.client import LLMClient
from src.models.conference import ConferenceConfig, ConferenceResult
from src.models.librarian import LibrarianConfig, LibrarianFile, LibrarianSummary


async def run_conference_async(
    query: str, 
    config: ConferenceConfig,
    api_key: str,
    enable_grounding: bool = True,
    enable_fragility: bool = True,
    fragility_tests: int = 3,
    fragility_model: str | None = None,
    librarian_files: Optional[list[LibrarianFile]] = None,
    librarian_config: Optional[LibrarianConfig] = None,
    progress_callback=None,
) -> tuple[ConferenceResult, Optional[LibrarianSummary]]:
    """Run the conference asynchronously.
    
    Args:
        query: The clinical question to deliberate on.
        config: Conference configuration with agents, topology, etc.
        api_key: OpenRouter API key.
        enable_grounding: Whether to verify citations against PubMed.
        enable_fragility: Whether to run fragility/stress testing.
        fragility_tests: Number of perturbation scenarios to test.
        fragility_model: Model to use for generating perturbations.
        librarian_files: Optional list of files for the Librarian to analyze.
        librarian_config: Optional Librarian configuration.
        progress_callback: Optional callback for progress updates.
        
    Returns:
        Tuple of (ConferenceResult, Optional[LibrarianSummary]).
    """
    client = LLMClient(api_key=api_key)
    
    # Process librarian files if provided
    librarian_summary: Optional[LibrarianSummary] = None
    agent_injection_prompts: Optional[dict[str, str]] = None
    librarian_service: Optional[LibrarianService] = None
    
    if librarian_files:
        # Report progress
        if progress_callback:
            progress_callback(ProgressUpdate(
                stage=ProgressStage.LIBRARIAN_ANALYSIS,
                message=f"Librarian analyzing {len(librarian_files)} document(s)...",
                percent=3,
                detail={"num_files": len(librarian_files)},
            ))
        
        # Initialize librarian
        librarian_service = LibrarianService(
            llm_client=client,
            config=librarian_config or LibrarianConfig(),
        )
        
        # Generate summary
        librarian_summary = await librarian_service.initialize(
            files=librarian_files,
            query=query,
        )
        
        # Report completion
        if progress_callback:
            progress_callback(ProgressUpdate(
                stage=ProgressStage.LIBRARIAN_ANALYSIS,
                message="Document analysis complete",
                percent=5,
                detail={
                    "num_files": len(librarian_files),
                    "input_tokens": librarian_summary.input_tokens,
                    "output_tokens": librarian_summary.output_tokens,
                },
            ))
        
        # Get summary text to inject into all agent prompts
        summary_text = librarian_service.get_summary_for_agents()
        if summary_text:
            # Inject into all agents
            agent_injection_prompts = {
                agent_config.agent_id: summary_text
                for agent_config in config.agents
            }
    
    # Create grounding engine if enabled
    grounding_engine = GroundingEngine() if enable_grounding else None
    
    engine = ConferenceEngine(client, grounding_engine=grounding_engine)
    result = await engine.run_conference(
        query=query, 
        config=config,
        enable_grounding=enable_grounding,
        enable_fragility=enable_fragility,
        fragility_tests=fragility_tests,
        fragility_model=fragility_model,
        agent_injection_prompts=agent_injection_prompts,
        progress_callback=progress_callback,
        librarian_service=librarian_service,  # Pass librarian for agent queries
    )
    
    return result, librarian_summary

