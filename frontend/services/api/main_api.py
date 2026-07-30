"""
SVACS — main_api.py
====================
Single FastAPI backend server for the SVACS dashboard.
Serves all data the frontend needs from one port (8000).
Acts as proxy for Samachar → SVACS intelligence flow.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import base64

BASE       = os.path.dirname(os.path.abspath(__file__))
ROOT       = os.path.join(BASE, "..")
DATA_LAYER = os.path.join(ROOT, "data_layer")
INTEL_DIR  = os.path.join(ROOT, "intelligence")

sys.path.insert(0, DATA_LAYER)
sys.path.insert(0, INTEL_DIR)

app = FastAPI(title="SVACS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PIPELINE_LOG = os.path.join(DATA_LAYER, "full_pipeline_log.jsonl")
TRACE_LOG    = os.path.join(ROOT, "..", "api", "ingestion_server", "trace_log.jsonl")
BUCKET_LOG   = os.path.join(DATA_LAYER, "bucket_verification_log.jsonl")
OBS_LOG      = os.path.join(DATA_LAYER, "execution_observability.jsonl")

SAMACHAR_URL = "https://showing-wizard-buffer.ngrok-free.dev/api/v1/intelligence/image"


def load_jsonl(path: str, limit: int = 100) -> list:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records[-limit:]


@app.get("/health")
def health():
    return {
        "status":               "ONLINE",
        "service":              "SVACS",
        "ws_connected":         False,
        "ingestion_rate":       18.4,
        "processing_latency_ms": 52,
        "uptime_seconds":       int(time.time() % 86400),
        "error_count_60s":      0,
        "last_telemetry_utc":   datetime.now(timezone.utc).isoformat(),
    }


@app.get("/signals")
def get_signals():
    records = load_jsonl(TRACE_LOG, limit=60)
    result  = []
    for i, r in enumerate(reversed(records)):
        result.append({
            "trace_id":       r.get("trace_id", f"trc_{i}"),
            "chunk_id":       f"sig_{i+1}",
            "vessel_id":      r.get("vessel_type", "unknown"),
            "source":         "ACOUSTIC",
            "ts_utc":         r.get("server_ts", datetime.now(timezone.utc).isoformat()),
            "frequency_band": "mixed",
        })
    return result


@app.get("/perception")
def get_perception():
    records = load_jsonl(PIPELINE_LOG, limit=60)
    result  = []
    for i, r in enumerate(reversed(records)):
        pe = r.get("perception_event", {})
        if not pe:
            continue
        result.append({
            "trace_id":         pe.get("trace_id", r.get("trace_id", f"trc_{i}")),
            "parent_chunk_id":  f"sig_{i+1}",
            "vessel_id":        pe.get("vessel_type", "unknown"),
            "confidence":       pe.get("confidence_score", 0.0),
            "kind":             "vessel_detection",
            "ts_utc":           datetime.now(timezone.utc).isoformat(),
            "vessel_class":     pe.get("vessel_type", "unknown"),
            "dominant_freq_hz": pe.get("dominant_freq_hz"),
            "anomaly_flag":     pe.get("anomaly_flag", False),
        })
    return result


@app.get("/intelligence")
def get_intelligence():
    records = load_jsonl(PIPELINE_LOG, limit=60)
    result  = []
    for i, r in enumerate(reversed(records)):
        ie = r.get("intelligence_event", {})
        if not ie:
            continue
        result.append({
            "trace_id":     ie.get("trace_id", r.get("trace_id", f"trc_{i}")),
            "vessel_id":    ie.get("vessel_type", "unknown"),
            "validation":   ie.get("validation_status", "FLAG"),
            "reasons":      [ie.get("explanation", "")[:80]] if ie.get("explanation") else ["pattern_match_ok"],
            "confidence":   ie.get("confidence", 0.0),
            "ts_utc":       datetime.now(timezone.utc).isoformat(),
            "vessel_class": ie.get("vessel_type", "unknown"),
            "risk_level":   ie.get("risk_level", "MEDIUM"),
        })
    return result


@app.get("/state-events")
def get_state_events():
    records = load_jsonl(PIPELINE_LOG, limit=60)
    result  = []
    for i, r in enumerate(reversed(records)):
        se = r.get("state_event", {})
        if not se or "error" in se:
            continue
        result.append({
            "trace_id":   se.get("trace_id", r.get("trace_id", f"trc_{i}")),
            "vessel_id":  se.get("vessel_type", "unknown"),
            "from_state": "NORMAL",
            "to_state":   se.get("state", "NORMAL"),
            "validation": se.get("short_label", "FLAG"),
            "confidence": r.get("intelligence_event", {}).get("confidence", 0.5),
            "ts_utc":     se.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })
    return result


@app.get("/vessels")
def get_vessels():
    records    = load_jsonl(PIPELINE_LOG, limit=100)
    vessel_map = {}
    for r in records:
        pe    = r.get("perception_event", {})
        ie    = r.get("intelligence_event", {})
        se    = r.get("state_event", {})
        vtype = pe.get("vessel_type") or ie.get("vessel_type") or "unknown"
        tid   = r.get("trace_id", "")
        vid   = vtype.upper() + "-" + tid[:8] if tid else vtype
        if vid not in vessel_map:
            vessel_map[vid] = {
                "vessel_id":          vid,
                "vessel_class":       vtype,
                "signal_count":       0,
                "perception_count":   0,
                "intelligence_count": 0,
                "state_count":        0,
                "last_state":         se.get("state", "NORMAL") if se else "NORMAL",
                "last_seen_utc":      datetime.now(timezone.utc).isoformat(),
                "status":             "NORMAL",
                "confidence":         pe.get("confidence_score", 0.0),
            }
        vessel_map[vid]["signal_count"]       += 1
        vessel_map[vid]["perception_count"]   += 1
        if ie:
            vessel_map[vid]["intelligence_count"] += 1
        if se and "error" not in se:
            vessel_map[vid]["state_count"] += 1
    return list(vessel_map.values())[:10]


@app.get("/alerts")
def get_alerts():
    records = load_jsonl(OBS_LOG, limit=20)
    result  = []
    for r in records:
        if r.get("event_type") == "ANOMALY_ESCALATION":
            result.append({
                "id":           str(uuid.uuid4()),
                "ts_utc":       r.get("obs_ts_human", datetime.now(timezone.utc).isoformat()),
                "vessel_id":    r.get("vessel_type", "unknown"),
                "kind":         "Anomaly Detected",
                "severity":     "HIGH" if r.get("risk_level") == "CRITICAL" else "MEDIUM",
                "message":      f"Anomaly escalation: {r.get('risk_level', 'UNKNOWN')}",
                "trace_id":     r.get("trace_id", ""),
                "acknowledged": False,
            })
    return result or [{
        "id":           "alert-1",
        "ts_utc":       datetime.now(timezone.utc).isoformat(),
        "vessel_id":    "unknown",
        "kind":         "System",
        "severity":     "LOW",
        "message":      "No anomalies detected",
        "acknowledged": False,
    }]


@app.get("/bucket/status")
def get_bucket_status():
    records = load_jsonl(BUCKET_LOG, limit=50)
    passed  = [r for r in records if r.get("status") == "PASS"]
    return {
        "sync_percent":  len(passed) / max(len(records), 1),
        "stages_synced": ["signal", "perception", "intelligence", "state"],
        "last_sync_utc": datetime.now(timezone.utc).isoformat(),
        "pending_writes": 0,
        "failed_writes": len(records) - len(passed),
    }


@app.get("/stage-metrics")
def get_stage_metrics():
    return [
        {"stage": "signal",       "total_events": 60,  "events_per_sec": 18.4, "p50_latency_ms": 12, "p95_latency_ms": 36,  "error_rate": 0.002, "status": "live"},
        {"stage": "perception",   "total_events": 58,  "events_per_sec": 17.2, "p50_latency_ms": 28, "p95_latency_ms": 78,  "error_rate": 0.004, "status": "live"},
        {"stage": "intelligence", "total_events": 54,  "events_per_sec": 16.1, "p50_latency_ms": 41, "p95_latency_ms": 110, "error_rate": 0.010, "status": "live"},
        {"stage": "state",        "total_events": 51,  "events_per_sec": 15.0, "p50_latency_ms": 22, "p95_latency_ms": 64,  "error_rate": 0.003, "status": "live"},
        {"stage": "bucket",       "total_events": 51,  "events_per_sec": 14.0, "p50_latency_ms": 18, "p95_latency_ms": 52,  "error_rate": 0.000, "status": "live"},
    ]


@app.get("/trace/{trace_id}")
def get_trace(trace_id: str):
    records = load_jsonl(PIPELINE_LOG, limit=200)
    for r in records:
        if r.get("trace_id") == trace_id:
            pe      = r.get("perception_event", {})
            ie      = r.get("intelligence_event", {})
            se      = r.get("state_event", {})
            missing = []
            if not pe: missing.append("perception")
            if not ie: missing.append("intelligence")
            if not se or "error" in se: missing.append("state")
            return {
                "trace_id":    trace_id,
                "signal":      {"trace_id": trace_id},
                "perception":  pe or None,
                "intelligence": ie or None,
                "state":       se if se and "error" not in se else None,
                "missing":     missing,
            }
    raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")


@app.post("/intelligence/image")
async def process_image(file: UploadFile = File(...)):
    """
    Accept image upload, proxy to Samachar, then run through SVACS intelligence.
    Avoids CORS by acting as proxy between frontend and Samachar.
    """
    try:
        import httpx
        from vessel_intelligence_engine import process_intelligence

        image_bytes = await file.read()

        # Compress image if too large
        from PIL import Image
        import io
        
        image = Image.open(io.BytesIO(image_bytes))
        if len(image_bytes) > 500_000:  # compress if > 500KB
            output = io.BytesIO()
            image = image.convert("RGB")
            image.save(output, format="JPEG", quality=50)
            image_bytes = output.getvalue()
            print(f"Compressed to {len(image_bytes)} bytes")

        # Forward to Samachar
        async with httpx.AsyncClient(timeout=180) as client:
            samachar_res = await client.post(
                SAMACHAR_URL,
                files={"image": (file.filename, image_bytes, file.content_type)},
            )

        if samachar_res.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Samachar error: {samachar_res.status_code}"
            )

        samachar_output = samachar_res.json()

        # Run through our intelligence engine
        result = process_intelligence(samachar_output)
        return result

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Samachar timed out")
    except Exception as e:
        print("ERROR in /intelligence/image:", str(e))
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/intelligence/samachar")
async def process_samachar_output(payload: dict):
    """
    Accept structured intelligence from Samachar and run through SVACS.
    Main integration endpoint for Samachar → SVACS flow.
    """
    try:
        from vessel_intelligence_engine import process_intelligence
        return process_intelligence(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline/run")
def run_pipeline_once():
    try:
        from hybrid_signal_builder import HybridSignalBuilder
        from perception_node import process_signal
        from vessel_intelligence_engine import process_intelligence

        builder = HybridSignalBuilder(seed=int(time.time()) % 1000)
        chunk   = builder.build("cargo")
        pe      = process_signal(chunk)

        local_input = {
            "trace_id":          chunk["trace_id"],
            "source_type":       "acoustic",
            "vessel_class":      pe.get("vessel_type", "unknown"),
            "confidence_score":  pe.get("confidence_score", 0.0),
            "visual_features":   [],
            "dimensions_estimate": {},
            "ais_data":          {},
        }
        ie = process_intelligence(local_input)
        return {
            "trace_id":          chunk["trace_id"],
            "vessel_class":      ie.get("vessel_class"),
            "confidence":        ie.get("confidence_score"),
            "risk_level":        ie.get("risk_level"),
            "explanation":       ie.get("explanation"),
            "validation_status": ie.get("validation_status"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))