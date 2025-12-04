"""Conference API routes with SSE streaming."""

import asyncio
import json
import os
import uuid
import time
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.schemas.conference import (
    ConferenceRequest,
    StreamEvent,
    StreamEventType,
)
from src.conference.engine import ConferenceEngine, create_default_config, ProgressStage, ProgressUpdate
from src.grounding.engine import GroundingEngine
from src.llm.client import LLMClient

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
