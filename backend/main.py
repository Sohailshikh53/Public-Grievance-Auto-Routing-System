"""
FastAPI Server Entrypoint
Public Grievance Auto-Routing System
"""

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database.db import init_db
from backend.database.seed_data import seed_database
from backend.routes.complaints import router as complaints_router
from backend.routes.analytics import router as analytics_router
from backend.routes.simulation import router as simulation_router
from backend.services.sla_service import evaluate_sla_and_escalate
from backend.config import ALLOWED_ORIGINS, CLASS_MARGIN_THRESHOLD, CONFIDENCE_THRESHOLD, MAHARASHTRA_CITIES

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and seed if empty
    init_db()
    seed_database()
    # Run initial SLA check
    evaluate_sla_and_escalate()
    stop_event = asyncio.Event()

    async def sla_watchdog():
        interval = max(30, int(os.getenv("PGARS_SLA_SCAN_SECONDS", "300")))
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                await asyncio.to_thread(evaluate_sla_and_escalate)

    watchdog_task = asyncio.create_task(sla_watchdog())
    try:
        yield
    finally:
        stop_event.set()
        await watchdog_task

app = FastAPI(
    title="Public Grievance Auto-Routing & SLA Redressal System API",
    version="1.0.0",
    description="Automated NLP complaint categorization, confidence threshold manual review fallback, and time-bound SLA escalation engine.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(complaints_router)
app.include_router(analytics_router)
app.include_router(simulation_router)

@app.post("/api/sla/trigger-check", tags=["sla"])
def trigger_sla_check():
    """Triggers an immediate SLA breach scan and auto-escalates overdue grievances."""
    res = evaluate_sla_and_escalate()
    return res

@app.get("/api/system/config", tags=["system"])
def get_public_system_config():
    return {
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "class_margin_threshold": CLASS_MARGIN_THRESHOLD,
        "supported_languages": ["English", "Hindi", "Marathi", "Hinglish / Roman Indic"],
        "state": "Maharashtra",
        "cities": MAHARASHTRA_CITIES,
    }

@app.post("/api/system/reset-demo-data", tags=["system"])
def reset_demo_data(confirm: bool = False):
    """Resets database and reloads default authentic grievance dataset."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to reset all grievance demo data.")
    seed_database(force=True)
    evaluate_sla_and_escalate()
    return {"success": True, "message": "Demo data reloaded and SLA evaluation synchronized."}

# Mount frontend directory for direct serving
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
