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
    V2ConferenceResponse,
    V2SynthesisResponse,
    ClinicalConsensusResponse,
    ExploratoryConsiderationResponse,
    TensionResponse,
    RoutingResponse,
    ScoutReportResponse,
    ScoutCitationResponse,
    LaneResultResponse,
    AgentResponse,
    ConferenceModeType,
)
from src.conference.engine import ConferenceEngine, create_default_config, ProgressStage, ProgressUpdate
from src.grounding.engine import GroundingEngine
from src.llm.client import LLMClient

# Import v2.1 components
from src.conference.engine_v2 import ConferenceEngineV2, V2ProgressStage, V2ProgressUpdate
from src.models.v2_schemas import PatientContext

# Import v3 learning orchestrator
from src.learning.orchestrator_v3 import ConferenceOrchestratorV3

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
async def start_conference(
    request: ConferenceRequest,
) -> dict:
    """
    Start a new conference and return a session ID.
    Use the session ID to stream results via SSE.
    """
    api_key = get_api_key()
    conference_id = str(uuid.uuid4())[:8]
    
    # Store conference config
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


@router.get("/conference/{conference_id}/stream")
async def stream_conference(
    conference_id: str,
) -> StreamingResponse:
    """
    Stream conference progress via Server-Sent Events.
    """
    if conference_id not in active_conferences:
        raise HTTPException(status_code=404, detail="Conference not found")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        conf_data = active_conferences[conference_id]
        request = conf_data["request"]
        api_key = conf_data["api_key"]
        
        try:
            # Emit start event
            yield format_sse(StreamEvent(
                event=StreamEventType.CONFERENCE_START,
                data={
                    "conference_id": conference_id,
                    "query": request.query,
                    "num_agents": len(request.agents),
                    "num_rounds": request.num_rounds,
                    "topology": request.topology.value,
                }
            ))
            
            # Build agent config
            agents_dict = {agent.role: agent.model for agent in request.agents}
            
            # Create conference config
            config = create_default_config(
                active_agents=agents_dict,
                arbitrator_model=request.arbitrator_model,
                num_rounds=request.num_rounds,
                topology=request.topology.value,
            )
            
            # Track state for streaming
            start_time = time.time()
            
            # Create async queue for progress events
            event_queue: asyncio.Queue = asyncio.Queue()
            
            def progress_callback(update: ProgressUpdate):
                """Convert progress updates to stream events."""
                event = None
                
                if update.stage == ProgressStage.ROUND_START:
                    event = StreamEvent(
                        event=StreamEventType.ROUND_START,
                        data={
                            "round_number": update.detail.get("round_number", 1),
                            "total_rounds": update.detail.get("total_rounds", request.num_rounds),
                        }
                    )
                elif update.stage == ProgressStage.AGENT_THINKING:
                    role_raw = update.detail.get("role", "")
                    role = str(role_raw).lower() if role_raw else ""
                    if hasattr(role_raw, 'value'):
                        role = role_raw.value
                    event = StreamEvent(
                        event=StreamEventType.AGENT_THINKING,
                        data={"role": role, "message": update.message}
                    )
                elif update.stage == ProgressStage.AGENT_COMPLETE:
                    role_raw = update.detail.get("role", "")
                    role = str(role_raw).lower() if role_raw else ""
                    if hasattr(role_raw, 'value'):
                        role = role_raw.value
                    event = StreamEvent(
                        event=StreamEventType.AGENT_COMPLETE,
                        data={
                            "role": role,
                            "content": update.detail.get("content", ""),
                            "confidence": update.detail.get("confidence", 0),
                            "changed": update.detail.get("changed", False),
                            "round_number": update.detail.get("round_number", 1),
                        }
                    )
                elif update.stage == ProgressStage.ROUND_COMPLETE:
                    event = StreamEvent(
                        event=StreamEventType.ROUND_COMPLETE,
                        data={"round_number": update.detail.get("round_number", 1)}
                    )
                elif update.stage == ProgressStage.GROUNDING:
                    verified = update.detail.get("verified")
                    if verified is not None:
                        event = StreamEvent(
                            event=StreamEventType.GROUNDING_COMPLETE,
                            data={
                                "verified": verified,
                                "failed": update.detail.get("failed", 0),
                            }
                        )
                    else:
                        event = StreamEvent(
                            event=StreamEventType.GROUNDING_START,
                            data={}
                        )
                elif update.stage == ProgressStage.ARBITRATION:
                    confidence = update.detail.get("confidence")
                    if confidence is not None:
                        event = StreamEvent(
                            event=StreamEventType.ARBITRATION_COMPLETE,
                            data={
                                "confidence": confidence,
                                "model": update.detail.get("model", ""),
                            }
                        )
                    else:
                        event = StreamEvent(
                            event=StreamEventType.ARBITRATION_START,
                            data={"model": update.detail.get("model", "")}
                        )
                elif update.stage == ProgressStage.FRAGILITY_START:
                    event = StreamEvent(
                        event=StreamEventType.FRAGILITY_START,
                        data={"num_tests": update.detail.get("num_tests", 0)}
                    )
                elif update.stage == ProgressStage.FRAGILITY_TEST:
                    event = StreamEvent(
                        event=StreamEventType.FRAGILITY_TEST,
                        data={
                            "test_number": update.detail.get("test_number", 1),
                            "total_tests": update.detail.get("total_tests", 1),
                            "outcome": update.detail.get("outcome", ""),
                            "perturbation": update.detail.get("perturbation", ""),
                        }
                    )
                elif update.stage == ProgressStage.LIBRARIAN_ANALYSIS:
                    input_tokens = update.detail.get("input_tokens")
                    if input_tokens:
                        event = StreamEvent(
                            event=StreamEventType.LIBRARIAN_COMPLETE,
                            data={"input_tokens": input_tokens}
                        )
                    else:
                        event = StreamEvent(
                            event=StreamEventType.LIBRARIAN_START,
                            data={"num_files": update.detail.get("num_files", 0)}
                        )
                
                if event:
                    # Put event in queue (sync callback, so we use put_nowait)
                    try:
                        event_queue.put_nowait(event)
                    except asyncio.QueueFull:
                        pass  # Drop if queue is full
            
            # Create LLM client
            llm_client = LLMClient(api_key=api_key)
            
            # Create grounding engine if enabled
            grounding_engine = GroundingEngine() if request.enable_grounding else None
            
            # Create engine with proper initialization
            engine = ConferenceEngine(
                llm_client=llm_client,
                grounding_engine=grounding_engine,
            )
            
            # Run conference in background task
            async def run_conference():
                try:
                    result = await engine.run_conference(
                        query=request.query,
                        config=config,
                        enable_grounding=request.enable_grounding,
                        enable_fragility=request.enable_fragility,
                        fragility_tests=request.fragility_tests,
                        fragility_model=request.fragility_model,
                        progress_callback=progress_callback,
                    )
                    return result
                except Exception as e:
                    await event_queue.put(StreamEvent(
                        event=StreamEventType.ERROR,
                        data={"message": str(e)}
                    ))
                    return None
            
            # Start conference task
            conference_task = asyncio.create_task(run_conference())
            
            # Stream events as they come in
            while not conference_task.done():
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield format_sse(event)
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
            
            # Drain remaining events
            while not event_queue.empty():
                event = await event_queue.get()
                yield format_sse(event)
            
            # Get result
            result = await conference_task
            
            if result:
                try:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Build rounds data carefully
                    rounds_data = []
                    for r in result.rounds:
                        responses_data = []
                        for resp in r.agent_responses.values():
                            role_str = str(resp.role.value) if hasattr(resp.role, 'value') else str(resp.role)
                            responses_data.append({
                                "role": role_str,
                                "model": resp.model,
                                "content": resp.content,
                                "confidence": resp.confidence,
                                "changed_from_previous": resp.changed_from_previous,
                            })
                        rounds_data.append({
                            "round_number": r.round_number,
                            "responses": responses_data,
                        })
                    
                    # Send complete event with full results
                    yield format_sse(StreamEvent(
                        event=StreamEventType.CONFERENCE_COMPLETE,
                        data={
                            "conference_id": result.conference_id,
                            "synthesis": {
                                "final_consensus": result.synthesis.final_consensus,
                                "confidence": result.synthesis.confidence,
                                "key_points": result.synthesis.key_points,
                            },
                            "dissent": {
                                "preserved": [result.dissent.summary] if result.dissent.preserved and result.dissent.summary else [],
                                "rationale": result.dissent.reasoning if result.dissent.preserved else "",
                            },
                            "rounds": rounds_data,
                            "grounding_report": result.grounding_report.model_dump() if result.grounding_report else None,
                            "fragility_report": result.fragility_report.model_dump() if result.fragility_report else None,
                            "total_tokens": result.token_usage.total_tokens,
                            "total_cost": result.token_usage.estimated_cost_usd,
                            "duration_ms": result.duration_ms,
                        }
                    ))
                except Exception as serialize_error:
                    print(f"Error serializing result: {serialize_error}")
                    import traceback
                    traceback.print_exc()
                    yield format_sse(StreamEvent(
                        event=StreamEventType.ERROR,
                        data={"message": f"Error serializing result: {str(serialize_error)}"}
                    ))
            else:
                # No result - check if we got an error event in the queue
                # If not, this is unexpected
                if event_queue.empty():
                    yield format_sse(StreamEvent(
                        event=StreamEventType.ERROR,
                        data={"message": "Conference ended without result"}
                    ))
            
            # Cleanup safely
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


# =============================================================================
# v2.1 CONFERENCE ENDPOINTS
# =============================================================================


@router.post("/conference/v2/start")
async def start_v2_conference(request: ConferenceRequest) -> dict:
    """
    Start a v2.1 conference with lane-based architecture.
    Returns a session ID for SSE streaming.
    """
    api_key = get_api_key()
    conference_id = f"v2_{str(uuid.uuid4())[:8]}"
    
    active_conferences[conference_id] = {
        "request": request,
        "api_key": api_key,
        "status": "pending",
        "created_at": time.time(),
        "version": "v2.1",
    }
    
    return {
        "conference_id": conference_id,
        "stream_url": f"/api/conference/v2/{conference_id}/stream",
        "version": "v2.1",
    }


@router.get("/conference/v2/{conference_id}/stream")
async def stream_v2_conference(conference_id: str) -> StreamingResponse:
    """Stream v2.1 conference progress via Server-Sent Events."""
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
                    "version": "v2.1",
                    "enable_scout": request.enable_scout,
                    "enable_routing": request.enable_routing,
                }
            ))
            
            start_time = time.time()
            event_queue: asyncio.Queue = asyncio.Queue()
            
            def v2_progress_callback(update: V2ProgressUpdate):
                """Convert v2 progress to stream events."""
                # Map v2 stages to stream event types
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
            
            # Build conference config for v2
            agents_dict = {agent.role: agent.model for agent in request.agents}
            config = create_default_config(
                active_agents=agents_dict,
                arbitrator_model=request.arbitrator_model,
                num_rounds=request.num_rounds,
                topology=request.topology.value,
            )
            
            # v3: Use orchestrator when learning is enabled
            enable_learning = getattr(request, 'enable_learning', True)
            
            async def run_v2_conference():
                try:
                    if enable_learning:
                        # Use orchestrator for learning-enabled conferences
                        orchestrator = ConferenceOrchestratorV3(llm_client=llm_client)
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
                            progress_callback=v2_progress_callback,
                        )
                        # Return the conference result (learning metadata stored internally)
                        return orchestrated_result.conference_result
                    else:
                        # Direct engine usage without learning
                        grounding_engine = GroundingEngine() if request.enable_grounding else None
                        engine = ConferenceEngineV2(
                            llm_client=llm_client,
                            grounding_engine=grounding_engine,
                        )
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
                            progress_callback=v2_progress_callback,
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
            conference_task = asyncio.create_task(run_v2_conference())
            
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
            
            print(f"V2 conference task completed, result: {result is not None}")
            
            if result:
                try:
                    duration_ms = int((time.time() - start_time) * 1000)
                    print(f"Serializing v2 result, duration: {duration_ms}ms")
                    
                    # Build v2 response structure
                    v2_data = serialize_v2_result(result, duration_ms)
                    print(f"V2 data serialized successfully, keys: {v2_data.keys()}")
                    
                    yield format_sse(StreamEvent(
                        event=StreamEventType.CONFERENCE_COMPLETE,
                        data=v2_data
                    ))
                    print("Sent conference_complete event")
                except Exception as serialize_error:
                    print(f"Error serializing v2 result: {serialize_error}")
                    import traceback
                    traceback.print_exc()
                    yield format_sse(StreamEvent(
                        event=StreamEventType.ERROR,
                        data={"message": f"Serialization error: {str(serialize_error)}"}
                    ))
            else:
                print("V2 conference task returned None")
            
            # Cleanup
            if conference_id in active_conferences:
                del active_conferences[conference_id]
                
        except Exception as e:
            print(f"V2 streaming error: {e}")
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


def serialize_v2_result(result, duration_ms: int) -> dict:
    """Serialize V2ConferenceResult to JSON-compatible dict."""
    # Routing
    mode_val = result.routing_decision.mode if isinstance(result.routing_decision.mode, str) else result.routing_decision.mode.value
    # v3: Include topology in routing data
    topology_val = result.routing_decision.topology if isinstance(result.routing_decision.topology, str) else result.routing_decision.topology.value
    routing_data = {
        "mode": mode_val,
        "active_agents": result.routing_decision.active_agents,
        "activate_scout": result.routing_decision.activate_scout,
        "rationale": result.routing_decision.routing_rationale or "",
        "complexity_signals": result.routing_decision.complexity_signals_detected,
        # v3: topology fields
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
