"""Conference API routes with SSE streaming."""

import asyncio
import json
import os
import uuid
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.schemas.conference import (
    ConferenceRequest,
    StreamEvent,
    StreamEventType,
    FullConferenceResponse,
    SynthesisResponse,
    ClinicalConsensusResponse,
    ExploratoryConsiderationResponse,
    TensionResponse,
    RoutingResponse,
    ScoutReportResponse,
    ScoutCitationResponse,
    LaneResultResponse,
    AgentResponse,
    ConferenceModeType,
    TopologyType,
)
from src.conference.engine import create_default_config
from src.conference.engine_v2 import ConferenceEngineV2, V2ProgressStage, V2ProgressUpdate
from src.grounding.engine import GroundingEngine
from src.llm.client import LLMClient
from src.models.v2_schemas import PatientContext
from src.learning.orchestrator_v3 import ConferenceOrchestratorV3, V3ModelConfig

router = APIRouter()

# In-memory store for active conferences (in production, use Redis)
active_conferences: dict = {}


def get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")
    return api_key


def format_sse(event: StreamEvent) -> str:
    """Format event for SSE."""
    return f"event: {event.event.value}\ndata: {json.dumps(event.data)}\n\n"


@router.post("/conference/start")
async def start_conference(request: ConferenceRequest) -> dict:
    """
    Start a new conference and return a session ID.
    Use the session ID to stream results via SSE.
    
    Uses two-lane architecture with intelligent routing and optional learning.
    """
    api_key = get_api_key()
    conference_id = str(uuid.uuid4())[:8]
    
    active_conferences[conference_id] = {
        "request": request,
        "api_key": api_key,
        "status": "pending",
        "created_at": time.time(),
    }
    
    return {
        "conference_id": conference_id,
        "stream_url": f"/api/conference/{conference_id}/stream",
    }


@router.get("/conference/{conference_id}/status")
async def get_conference_status(conference_id: str) -> dict:
    """Get status of a conference."""
    if conference_id not in active_conferences:
        raise HTTPException(status_code=404, detail="Conference not found or completed")
    
    conf_data = active_conferences[conference_id]
    return {
        "conference_id": conference_id,
        "status": conf_data["status"],
        "created_at": conf_data["created_at"],
    }


@router.get("/conference/{conference_id}/stream")
async def stream_conference(conference_id: str) -> StreamingResponse:
    """Stream conference progress via Server-Sent Events."""
    if conference_id not in active_conferences:
        raise HTTPException(status_code=404, detail="Conference not found")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        conf_data = active_conferences[conference_id]
        request: ConferenceRequest = conf_data["request"]
        api_key = conf_data["api_key"]
        
        try:
            # Emit start event
            yield format_sse(StreamEvent(
                event=StreamEventType.CONFERENCE_START,
                data={
                    "conference_id": conference_id,
                    "query": request.query,
                    "num_agents": len(request.agents),
                    "enable_scout": request.enable_scout,
                    "enable_routing": request.enable_routing,
                    "enable_learning": request.enable_learning,
                }
            ))
            
            start_time = time.time()
            event_queue: asyncio.Queue = asyncio.Queue()
            
            def progress_callback(update: V2ProgressUpdate):
                """Convert progress updates to stream events."""
                # Map stages to stream event types
                stage_event_map = {
                    V2ProgressStage.INITIALIZING: StreamEventType.CONFERENCE_START,
                    V2ProgressStage.ROUTING: StreamEventType.ROUTING_START,
                    V2ProgressStage.SCOUT_SEARCHING: StreamEventType.SCOUT_START,
                    V2ProgressStage.SCOUT_COMPLETE: StreamEventType.SCOUT_COMPLETE,
                    V2ProgressStage.LANE_A_START: StreamEventType.LANE_A_START,
                    V2ProgressStage.LANE_A_AGENT: StreamEventType.LANE_A_AGENT,
                    V2ProgressStage.LANE_A_COMPLETE: StreamEventType.LANE_A_COMPLETE,
                    V2ProgressStage.LANE_B_START: StreamEventType.LANE_B_START,
                    V2ProgressStage.LANE_B_AGENT: StreamEventType.LANE_B_AGENT,
                    V2ProgressStage.LANE_B_COMPLETE: StreamEventType.LANE_B_COMPLETE,
                    V2ProgressStage.CROSS_EXAMINATION: StreamEventType.CROSS_EXAM_START,
                    V2ProgressStage.FEASIBILITY: StreamEventType.FEASIBILITY_START,
                    V2ProgressStage.GROUNDING: StreamEventType.GROUNDING_START,
                    V2ProgressStage.ARBITRATION: StreamEventType.ARBITRATION_START,
                    V2ProgressStage.FRAGILITY_START: StreamEventType.FRAGILITY_START,
                    V2ProgressStage.FRAGILITY_TEST: StreamEventType.FRAGILITY_TEST,
                    # Don't map COMPLETE to CONFERENCE_COMPLETE - the final event is sent separately with full data
                    # V2ProgressStage.COMPLETE: StreamEventType.CONFERENCE_COMPLETE,
                    V2ProgressStage.ERROR: StreamEventType.ERROR,
                }
                
                # Skip COMPLETE stage - we send the full result separately at the end
                if update.stage == V2ProgressStage.COMPLETE:
                    return
                
                event_type = stage_event_map.get(update.stage, StreamEventType.CONFERENCE_START)
                
                event = StreamEvent(
                    event=event_type,
                    data={
                        "message": update.message,
                        "percent": update.percent,
                        **update.detail,
                    }
                )
                
                try:
                    event_queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
            
            # Create patient context if provided
            patient_context = None
            if request.patient_context:
                patient_context = PatientContext(
                    age=request.patient_context.age,
                    sex=request.patient_context.sex,
                    comorbidities=request.patient_context.comorbidities,
                    current_medications=request.patient_context.current_medications,
                    allergies=request.patient_context.allergies,
                    failed_treatments=request.patient_context.failed_treatments,
                    relevant_history=request.patient_context.relevant_history,
                    constraints=request.patient_context.constraints,
                )
            
            # Create LLM client
            llm_client = LLMClient(api_key=api_key)
            
            # Build conference config
            agents_dict = {agent.role: agent.model for agent in request.agents}
            # Use topology_override if provided, otherwise router decides
            topology_str = request.topology_override.value if request.topology_override else "free_discussion"
            config = create_default_config(
                active_agents=agents_dict,
                arbitrator_model=request.arbitrator_model,
                num_rounds=2,  # Rounds are managed by lane executor now
                topology=topology_str,
            )
            
            # Use orchestrator when learning is enabled
            enable_learning = request.enable_learning
            
            # Build model config if provided
            model_config = None
            if request.model_config_v3:
                model_config = V3ModelConfig.from_dict({
                    "router_model": request.model_config_v3.router_model,
                    "classifier_model": request.model_config_v3.classifier_model,
                    "surgeon_model": request.model_config_v3.surgeon_model,
                    "scout_model": request.model_config_v3.scout_model,
                    "validator_model": request.model_config_v3.validator_model,
                })
            
            # Extract overrides for routing
            mode_override = request.mode_override.value if request.mode_override else None
            topology_override = request.topology_override.value if request.topology_override else None
            
            async def run_conference_task():
                try:
                    if enable_learning:
                        # Use orchestrator for learning-enabled conferences
                        orchestrator = ConferenceOrchestratorV3(
                            llm_client=llm_client,
                            model_config=model_config,
                        )
                        orchestrated_result = await orchestrator.run(
                            query=request.query,
                            config=config,
                            patient_context=patient_context,
                            enable_routing=request.enable_routing,
                            enable_scout=request.enable_scout,
                            enable_grounding=request.enable_grounding,
                            enable_fragility=request.enable_fragility,
                            fragility_tests=request.fragility_tests,
                            enable_learning=True,
                            enable_injection=True,
                            mode_override=mode_override,
                            topology_override=topology_override,
                            progress_callback=progress_callback,
                        )
                        return orchestrated_result.conference_result
                    else:
                        # Direct engine usage without learning
                        grounding_engine = GroundingEngine() if request.enable_grounding else None
                        engine = ConferenceEngineV2(
                            llm_client=llm_client,
                            grounding_engine=grounding_engine,
                        )
                        router_model = model_config.router_model if model_config else None
                        result = await engine.run_conference(
                            query=request.query,
                            config=config,
                            patient_context=patient_context,
                            enable_routing=request.enable_routing,
                            enable_scout=request.enable_scout,
                            enable_grounding=request.enable_grounding,
                            enable_fragility=request.enable_fragility,
                            fragility_tests=request.fragility_tests,
                            fragility_model=request.fragility_model,
                            router_model=router_model,
                            mode_override=mode_override,
                            topology_override=topology_override,
                            progress_callback=progress_callback,
                        )
                        return result
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await event_queue.put(StreamEvent(
                        event=StreamEventType.ERROR,
                        data={"message": str(e)}
                    ))
                    return None
            
            # Start conference task
            conference_task = asyncio.create_task(run_conference_task())
            
            # Stream events
            while not conference_task.done():
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield format_sse(event)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
            
            # Drain remaining events
            while not event_queue.empty():
                event = await event_queue.get()
                yield format_sse(event)
            
            # Get result
            result = await conference_task
            
            print(f"Conference task completed, result: {result is not None}")
            
            if result:
                try:
                    duration_ms = int((time.time() - start_time) * 1000)
                    print(f"Serializing result, duration: {duration_ms}ms")
                    
                    # Build response structure
                    response_data = serialize_result(result, duration_ms)
                    print(f"Data serialized successfully, keys: {response_data.keys()}")
                    
                    yield format_sse(StreamEvent(
                        event=StreamEventType.CONFERENCE_COMPLETE,
                        data=response_data
                    ))
                    print("Sent conference_complete event")
                except Exception as serialize_error:
                    print(f"Error serializing result: {serialize_error}")
                    import traceback
                    traceback.print_exc()
                    yield format_sse(StreamEvent(
                        event=StreamEventType.ERROR,
                        data={"message": f"Serialization error: {str(serialize_error)}"}
                    ))
            else:
                print("Conference task returned None")
            
            # Cleanup
            if conference_id in active_conferences:
                del active_conferences[conference_id]
                
        except Exception as e:
            print(f"Streaming error: {e}")
            import traceback
            traceback.print_exc()
            yield format_sse(StreamEvent(
                event=StreamEventType.ERROR,
                data={"message": str(e)}
            ))
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def serialize_result(result, duration_ms: int) -> dict:
    """Serialize conference result to JSON-compatible dict."""
    # Routing
    mode_val = result.routing_decision.mode if isinstance(result.routing_decision.mode, str) else result.routing_decision.mode.value
    topology_val = result.routing_decision.topology if isinstance(result.routing_decision.topology, str) else result.routing_decision.topology.value
    routing_data = {
        "mode": mode_val,
        "active_agents": result.routing_decision.active_agents,
        "activate_scout": result.routing_decision.activate_scout,
        "rationale": result.routing_decision.routing_rationale or "",
        "complexity_signals": result.routing_decision.complexity_signals_detected,
        "topology": topology_val,
        "topology_rationale": result.routing_decision.topology_rationale or "",
        "topology_signals": result.routing_decision.topology_signals_detected,
    }
    
    # Scout report
    scout_data = None
    if result.scout_report:
        scout_data = {
            "is_empty": result.scout_report.is_empty,
            "query_keywords": result.scout_report.query_keywords,
            "total_found": result.scout_report.total_results_found,
            "meta_analyses": [serialize_citation(c) for c in result.scout_report.meta_analyses],
            "high_quality_rcts": [serialize_citation(c) for c in result.scout_report.high_quality_rcts],
            "preliminary_evidence": [serialize_citation(c) for c in result.scout_report.preliminary_evidence],
            "conflicting_evidence": [serialize_citation(c) for c in result.scout_report.conflicting_evidence],
        }
    
    # Lane A
    lane_a_data = None
    if result.lane_a_result:
        lane_a_data = {
            "lane": "A",
            "responses": [
                {
                    "role": resp.role,
                    "model": resp.model,
                    "content": resp.content,
                    "confidence": resp.confidence,
                    "changed_from_previous": False,
                }
                for resp in result.lane_a_result.agent_responses.values()
            ]
        }
    
    # Lane B
    lane_b_data = None
    if result.lane_b_result:
        lane_b_data = {
            "lane": "B",
            "responses": [
                {
                    "role": resp.role,
                    "model": resp.model,
                    "content": resp.content,
                    "confidence": resp.confidence,
                    "changed_from_previous": False,
                }
                for resp in result.lane_b_result.agent_responses.values()
            ]
        }
    
    # Synthesis
    synthesis_data = {
        "clinical_consensus": {
            "recommendation": result.synthesis.clinical_consensus.recommendation,
            "evidence_basis": result.synthesis.clinical_consensus.evidence_basis,
            "confidence": result.synthesis.clinical_consensus.confidence,
            "safety_profile": result.synthesis.clinical_consensus.safety_profile,
            "contraindications": result.synthesis.clinical_consensus.contraindications,
        },
        "exploratory_considerations": [
            {
                "hypothesis": e.hypothesis,
                "mechanism": e.mechanism,
                "evidence_level": e.evidence_level,
                "potential_benefit": e.potential_benefit,
                "risks": e.risks,
                "what_would_validate": e.what_would_validate,
            }
            for e in result.synthesis.exploratory_considerations
        ],
        "tensions": [
            {
                "description": t.description,
                "lane_a_position": t.lane_a_position,
                "lane_b_position": t.lane_b_position,
                "resolution": t.resolution,
            }
            for t in result.synthesis.tensions
        ],
        "safety_concerns": result.synthesis.safety_concerns_raised,
        "stagnation_concerns": result.synthesis.stagnation_concerns_raised,
        "what_would_change": result.synthesis.what_would_change_mind,
        "preserved_dissent": result.synthesis.preserved_dissent,
        "overall_confidence": result.synthesis.overall_confidence,
    }
    
    # Fragility report
    fragility_data = None
    if result.fragility_report and hasattr(result.fragility_report, 'results'):
        fragility_data = {
            "perturbations_tested": result.fragility_report.perturbations_tested,
            "survival_rate": result.fragility_report.survival_rate,
            "is_fragile": result.fragility_report.is_fragile,
            "results": [
                {
                    "perturbation": r.perturbation,
                    "outcome": r.outcome.value if hasattr(r.outcome, 'value') else r.outcome,
                    "explanation": r.explanation,
                    "modified_recommendation": r.modified_recommendation,
                }
                for r in result.fragility_report.results
            ]
        }
    
    result_mode = result.mode if isinstance(result.mode, str) else result.mode.value
    return {
        "conference_id": result.conference_id,
        "query": result.query,
        "mode": result_mode,
        "routing": routing_data,
        "scout_report": scout_data,
        "lane_a": lane_a_data,
        "lane_b": lane_b_data,
        "synthesis": synthesis_data,
        "fragility_report": fragility_data,
        "total_tokens": result.token_usage.total_tokens,
        "total_cost": result.token_usage.estimated_cost_usd,
        "duration_ms": duration_ms,
    }


def serialize_citation(citation) -> dict:
    """Serialize a ScoutCitation to dict."""
    return {
        "title": citation.title,
        "authors": citation.authors,
        "journal": citation.journal,
        "year": citation.year,
        "pmid": citation.pmid,
        "evidence_grade": citation.evidence_grade.value,
        "key_finding": citation.key_finding,
    }
