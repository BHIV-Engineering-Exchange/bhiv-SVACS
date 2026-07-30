"""
State Engine HTTP API
=====================
Receives live intelligence_event payloads from NICAI/Sanskar and returns the
deterministic state_event produced by the State Engine.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from schemas.state_event import IntelligenceEvent, StateEvent
from state_engine import StateEngine
from trace_validator import TraceContinuityError, TraceValidationError


app = FastAPI(title="SVACS State Engine", version="1.0.0")
engine = StateEngine(bucket_log_path="logs/live_bucket.jsonl")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "stage": "state_engine"}


@app.post("/ingest/intelligence", response_model=StateEvent)
def ingest_intelligence(event: IntelligenceEvent) -> StateEvent:
    try:
        return engine.process(event)
    except (TraceValidationError, TraceContinuityError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
