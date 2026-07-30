"""
SVACS Ingestion Server — mock_server.py  (SNR + Dual Endpoint + Perception Bridge)
====================================================================================
CHANGES for Task: Signal → Perception Integration + SNR Fix
  1. Added /ingest endpoint (PRIMARY alias for /ingest/signal)
  2. Both endpoints share IDENTICAL validation + logic via _handle_ingest()
  3. Perception node called inline — real perception_event generated per chunk
  4. Latency tracked per event (ingest_received_time → perception_output_time)
  5. Logs include full signal_chunk → perception_event transformation

Endpoints:
  POST /ingest          ← PRIMARY (new, same as /ingest/signal)
  POST /ingest/signal   ← ALIAS  (existing, unchanged behaviour)
  GET  /health          ← includes avg_latency_ms + max_latency_ms
  GET  /perception_log  ← returns last N perception events as JSON

Logs:
  api/ingestion_server/ingestion_log.jsonl   ← all ingest attempts
  api/ingestion_server/trace_log.jsonl       ← trace continuity log
  api/ingestion_server/perception_log.jsonl  ← signal→perception transformations
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import json
import os
import sys
import time
import re

# ── Import perception node ───────────────────────────────────────────────────
# Adjust path so mock_server can find perception_node wherever it's run from
_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_LAYER  = os.path.join(os.path.dirname(_SERVER_DIR), "services", "data_layer")
for _p in [_DATA_LAYER, os.path.join(_SERVER_DIR, "..", "services", "data_layer"),
           os.getcwd(), _SERVER_DIR]:
    if os.path.exists(os.path.join(_p, "perception_node.py")):
        sys.path.insert(0, _p)
        break

try:
    from perception_node import process_signal
    PERCEPTION_AVAILABLE = True
    print("[SERVER] perception_node imported successfully")
except ImportError as e:
    PERCEPTION_AVAILABLE = False
    print(f"[SERVER][WARN] perception_node not found: {e}")
    print("[SERVER][WARN] Perception events will be skipped")

app = FastAPI()

# ── In-memory store ──────────────────────────────────────────────────────────
received          = []    # accepted trace_ids
error_log         = []    # rejection reasons
perception_events = []    # full transformation log
latency_ms_list   = []    # latency per event in ms

# ── Log files ────────────────────────────────────────────────────────────────
_DIR            = os.path.dirname(os.path.abspath(__file__))
LOG_FILE        = os.path.join(_DIR, "ingestion_log.jsonl")
TRACE_LOG       = os.path.join(_DIR, "trace_log.jsonl")
PERCEPTION_LOG  = os.path.join(_DIR, "perception_log.jsonl")

UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)
VALID_VESSEL_TYPES = {"cargo", "speedboat", "submarine", "low_confidence", "anomaly", "unknown"}


def write_log(entry: dict, path: str = None):
    target = path or LOG_FILE
    with open(target, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def validate_chunk(chunk: dict):
    required = ["trace_id", "timestamp", "samples", "sample_rate", "vessel_type"]
    for field in required:
        if field not in chunk:
            return False, f"Missing required field: '{field}'"

    trace_id = chunk["trace_id"]
    if not isinstance(trace_id, str) or not trace_id:
        return False, "trace_id must be a non-empty string"
    if not UUID_RE.match(trace_id):
        return False, f"trace_id is not a valid UUID4: '{trace_id}'"

    samples = chunk["samples"]
    if not isinstance(samples, list):
        return False, "samples must be an array"
    if len(samples) == 0:
        return False, "samples array is empty"

    if not isinstance(chunk["sample_rate"], (int, float)) or chunk["sample_rate"] <= 0:
        return False, "sample_rate must be a positive number"

    if not isinstance(chunk["timestamp"], (int, float)):
        return False, "timestamp must be a number"

    vessel = chunk["vessel_type"]
    if vessel not in VALID_VESSEL_TYPES:
        return False, f"vessel_type '{vessel}' is not valid. Must be one of: {VALID_VESSEL_TYPES}"

    return True, None


# ── Shared handler (used by BOTH /ingest and /ingest/signal) ─────────────────

async def _handle_ingest(request: Request, endpoint_name: str):
    """
    Single shared handler for both POST /ingest and POST /ingest/signal.
    Logic, validation, and response are IDENTICAL — endpoint_name is logged only.
    """
    ingest_received_time = time.time()

    log_entry = {
        "event":     "ingest_attempt",
        "endpoint":  endpoint_name,
        "server_ts": round(ingest_received_time, 4),
        "client_ip": request.client.host,
    }

    # Step 1: Parse JSON
    try:
        chunk = await request.json()
    except Exception:
        log_entry.update({"status": "REJECTED", "reason": "Body is not valid JSON", "trace_id": None})
        write_log(log_entry)
        return JSONResponse(status_code=400, content={"status": "error", "reason": "Body is not valid JSON"})

    # Step 2: Validate schema
    ok, reason = validate_chunk(chunk)
    if not ok:
        log_entry.update({
            "status":     "REJECTED",
            "reason":     reason,
            "trace_id":   chunk.get("trace_id"),
            "vessel_type": chunk.get("vessel_type"),
        })
        write_log(log_entry)
        error_log.append(reason)
        return JSONResponse(status_code=422, content={"status": "error", "reason": reason})

    # Step 3: Accept — run perception node
    trace_id = chunk["trace_id"]
    vessel   = chunk["vessel_type"]
    n        = len(chunk["samples"])
    anomaly  = chunk.get("expected_label", {}).get("anomaly_flag", False)
    snr      = chunk.get("snr_db", "N/A")

    perception_event = None
    latency_ms       = None

    if PERCEPTION_AVAILABLE:
        perception_output_time = time.time()
        try:
            perception_event = process_signal(chunk)
        except Exception as exc:
            perception_event = {"error": True, "reason": str(exc), "trace_id": trace_id}
        latency_ms = round((time.time() - ingest_received_time) * 1000, 3)
        latency_ms_list.append(latency_ms)

        # Log full transformation
        transformation = {
            "trace_id":          trace_id,
            "input_vessel":      vessel,
            "predicted_vessel":  perception_event.get("vessel_type"),
            "confidence":        perception_event.get("confidence_score"),
            "dominant_freq":     perception_event.get("dominant_freq_hz"),
            "anomaly":           perception_event.get("anomaly_flag"),
            "snr_db":            snr,
            "latency_ms":        latency_ms,
            "ingest_ts":         round(ingest_received_time, 4),
            "perception_ts":     round(time.time(), 4),
        }
        write_log(transformation, PERCEPTION_LOG)
        perception_events.append(transformation)

    log_entry.update({
        "status":      "ACCEPTED",
        "trace_id":    trace_id,
        "vessel_type": vessel,
        "samples":     n,
        "anomaly_flag": anomaly,
        "snr_db":      snr,
        "chunk_ts":    chunk.get("timestamp"),
        "latency_ms":  latency_ms,
    })
    write_log(log_entry)
    received.append(trace_id)

    write_log({
        "stage":       "signal_ingest",
        "trace_id":    trace_id,
        "vessel_type": vessel,
        "chunk_ts":    chunk.get("timestamp"),
        "server_ts":   round(time.time(), 4)
    }, TRACE_LOG)

    print(
        f"[{endpoint_name}] trace={trace_id[:8]}...  "
        f"vessel={vessel:<16}  samples={n}  "
        f"snr={snr}  latency={latency_ms}ms"
    )

    response = {"status": "ok", "trace_id": trace_id}
    if perception_event and "error" not in perception_event:
        response["perception_event"] = perception_event

    return JSONResponse(status_code=200, content=response)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/ingest")
async def ingest_primary(request: Request):
    """PRIMARY endpoint — same logic as /ingest/signal"""
    return await _handle_ingest(request, "/ingest")


@app.post("/ingest/signal")
async def ingest_signal(request: Request):
    """ALIAS endpoint — same logic as /ingest"""
    return await _handle_ingest(request, "/ingest/signal")


@app.get("/health")
def health():
    avg_lat = round(sum(latency_ms_list) / len(latency_ms_list), 3) if latency_ms_list else None
    max_lat = round(max(latency_ms_list), 3) if latency_ms_list else None
    return {
        "status":            "alive",
        "chunks_received":   len(received),
        "chunks_rejected":   len(error_log),
        "perception_events": len(perception_events),
        "avg_latency_ms":    avg_lat,
        "max_latency_ms":    max_lat,
        "log_file":          LOG_FILE,
        "trace_log":         TRACE_LOG,
        "perception_log":    PERCEPTION_LOG,
    }


@app.get("/perception_log")
def get_perception_log(limit: int = 20):
    """Return the last N perception events for inspection."""
    return {
        "count":  len(perception_events),
        "events": perception_events[-limit:]
    }


if __name__ == "__main__":
    print(f"[SERVER] Ingestion log   : {LOG_FILE}")
    print(f"[SERVER] Trace log       : {TRACE_LOG}")
    print(f"[SERVER] Perception log  : {PERCEPTION_LOG}")
    print(f"[SERVER] Endpoints       : POST /ingest  POST /ingest/signal  GET /health")
    print(f"[SERVER] Starting on     : http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)