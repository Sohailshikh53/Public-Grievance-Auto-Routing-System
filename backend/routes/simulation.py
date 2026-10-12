"""Scenario simulation API routes."""

from typing import Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.simulation_service import list_presets, run_simulation


router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class SimulationRequest(BaseModel):
    preset: str = "normal"
    seed: int = Field(42, ge=1, le=999999)
    duration_hours: Optional[float] = Field(None, ge=1, le=168)
    arrival_rate: Optional[float] = Field(None, ge=0.5, le=100)
    confidence_threshold: float = Field(0.65, ge=0.3, le=0.95)
    ambiguity_rate: Optional[float] = Field(None, ge=0, le=0.9)
    high_urgency_rate: Optional[float] = Field(None, ge=0, le=0.9)
    triage_staff: int = Field(4, ge=1, le=50)
    staffing: Optional[Dict[str, int]] = None
    city_scope: Optional[str] = None


@router.get("/presets")
def get_simulation_presets():
    return {"presets": list_presets()}


@router.post("/run")
def simulate(req: SimulationRequest):
    return run_simulation(req.model_dump())
