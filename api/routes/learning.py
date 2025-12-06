"""
API routes for learning data.

Provides read-only access to the Experience Library and Speculation Library.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

DATA_DIR = Path("data")

# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class HeuristicResponse(BaseModel):
    id: str
    query_template: str
    category: str
    heuristic: str
    confidence: float
    success_rate: float
    times_used: int
    source_conference: Optional[str]
    created_at: Optional[str]
    
class SpeculationResponse(BaseModel):
    id: str
    hypothesis: str
    mechanism: str
    evidence_level: str
    source_conference: Optional[str]
    lane: str
    status: str
    watch_keywords: list[str]
    created_at: Optional[str]
    
class LearningStatsResponse(BaseModel):
    total_heuristics: int
    total_speculations: int
    categories: dict[str, int]
    speculation_statuses: dict[str, int]
    avg_heuristic_confidence: float
    total_heuristic_uses: int
    
# ============================================================================
# ROUTES
# ============================================================================

@router.get("/learning/heuristics")
async def get_heuristics(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """
    Get stored heuristics from the Experience Library.
    
    Args:
        category: Filter by category (optional)
        limit: Maximum number of results
        offset: Pagination offset
    """
    library_path = DATA_DIR / "experience_library_v3.json"
    
    if not library_path.exists():
        return {"heuristics": [], "total": 0}
    
    try:
        with open(library_path, "r") as f:
            data = json.load(f)
        
        heuristics = data.get("heuristics", [])
        
        # Filter by category if specified
        if category:
            heuristics = [h for h in heuristics if h.get("category") == category]
        
        total = len(heuristics)
        
        # Apply pagination
        heuristics = heuristics[offset:offset + limit]
        
        # Format for response
        formatted = []
        for h in heuristics:
            formatted.append({
                "id": h.get("id", ""),
                "query_template": h.get("query_template", ""),
                "category": h.get("category", "general"),
                "heuristic": h.get("heuristic", ""),
                "confidence": h.get("confidence", 0.0),
                "success_rate": h.get("metadata", {}).get("success_rate", 0.0),
                "times_used": h.get("metadata", {}).get("times_used", 0),
                "source_conference": h.get("source_conference"),
                "created_at": h.get("created_at"),
            })
        
        return {"heuristics": formatted, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load heuristics: {str(e)}")

@router.get("/learning/speculations")
async def get_speculations(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """
    Get stored speculations from the Speculation Library.
    
    Args:
        status: Filter by status (active, promoted, deprecated, etc.)
        limit: Maximum number of results
        offset: Pagination offset
    """
    library_path = DATA_DIR / "speculation_library.json"
    
    if not library_path.exists():
        return {"speculations": [], "total": 0}
    
    try:
        with open(library_path, "r") as f:
            data = json.load(f)
        
        speculations = list(data.get("speculations", {}).values())
        
        # Filter by status if specified
        if status:
            speculations = [s for s in speculations if s.get("status") == status]
        
        total = len(speculations)
        
        # Apply pagination
        speculations = speculations[offset:offset + limit]
        
        # Format for response
        formatted = []
        for s in speculations:
            formatted.append({
                "id": s.get("id", ""),
                "hypothesis": s.get("hypothesis", ""),
                "mechanism": s.get("mechanism", ""),
                "evidence_level": s.get("evidence_level", ""),
                "source_conference": s.get("source_conference"),
                "lane": s.get("lane", "B"),
                "status": s.get("status", "active"),
                "watch_keywords": s.get("watch_keywords", []),
                "created_at": s.get("created_at"),
            })
        
        return {"speculations": formatted, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load speculations: {str(e)}")

@router.get("/learning/stats")
async def get_learning_stats() -> LearningStatsResponse:
    """Get aggregate statistics about the learning system."""
    
    total_heuristics = 0
    total_speculations = 0
    categories: dict[str, int] = {}
    speculation_statuses: dict[str, int] = {}
    avg_confidence = 0.0
    total_uses = 0
    
    # Load experience library
    exp_path = DATA_DIR / "experience_library_v3.json"
    if exp_path.exists():
        try:
            with open(exp_path, "r") as f:
                data = json.load(f)
            
            heuristics = data.get("heuristics", [])
            total_heuristics = len(heuristics)
            
            # Category counts
            for h in heuristics:
                cat = h.get("category", "general")
                categories[cat] = categories.get(cat, 0) + 1
                
                # Sum confidence and uses
                avg_confidence += h.get("confidence", 0.0)
                total_uses += h.get("metadata", {}).get("times_used", 0)
            
            if total_heuristics > 0:
                avg_confidence /= total_heuristics
        except Exception:
            pass
    
    # Load speculation library
    spec_path = DATA_DIR / "speculation_library.json"
    if spec_path.exists():
        try:
            with open(spec_path, "r") as f:
                data = json.load(f)
            
            speculations = data.get("speculations", {})
            total_speculations = len(speculations)
            
            # Status counts
            for s in speculations.values():
                status = s.get("status", "active")
                speculation_statuses[status] = speculation_statuses.get(status, 0) + 1
        except Exception:
            pass
    
    return LearningStatsResponse(
        total_heuristics=total_heuristics,
        total_speculations=total_speculations,
        categories=categories,
        speculation_statuses=speculation_statuses,
        avg_heuristic_confidence=round(avg_confidence, 2),
        total_heuristic_uses=total_uses,
    )

@router.delete("/learning/heuristics/{heuristic_id}")
async def delete_heuristic(heuristic_id: str) -> dict:
    """Delete a heuristic from the Experience Library."""
    library_path = DATA_DIR / "experience_library_v3.json"
    
    if not library_path.exists():
        raise HTTPException(status_code=404, detail="Experience library not found")
    
    try:
        with open(library_path, "r") as f:
            data = json.load(f)
        
        heuristics = data.get("heuristics", [])
        original_count = len(heuristics)
        
        data["heuristics"] = [h for h in heuristics if h.get("id") != heuristic_id]
        
        if len(data["heuristics"]) == original_count:
            raise HTTPException(status_code=404, detail="Heuristic not found")
        
        with open(library_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return {"deleted": True, "id": heuristic_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete heuristic: {str(e)}")

@router.delete("/learning/speculations/{speculation_id}")
async def delete_speculation(speculation_id: str) -> dict:
    """Delete a speculation from the Speculation Library."""
    library_path = DATA_DIR / "speculation_library.json"
    
    if not library_path.exists():
        raise HTTPException(status_code=404, detail="Speculation library not found")
    
    try:
        with open(library_path, "r") as f:
            data = json.load(f)
        
        speculations = data.get("speculations", {})
        
        if speculation_id not in speculations:
            raise HTTPException(status_code=404, detail="Speculation not found")
        
        del speculations[speculation_id]
        data["speculations"] = speculations
        
        with open(library_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return {"deleted": True, "id": speculation_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete speculation: {str(e)}")

