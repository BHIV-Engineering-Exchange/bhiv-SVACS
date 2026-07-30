"""
SVACS — perception_integration.py
===================================
PHASE 5 | Live Pipeline Integration

Connects perception_node to the live ingestion stream.
Sends signal_chunks → perception_node → logs perception_events.

Demonstrates end-to-end:
  signal_chunk (from HybridSignalBuilder)
      → POST /ingest/signal (mock_server)
          → process_signal() (perception_node)
              → perception_event logged with trace_id proof

Run from: svacs-demo/services/data_layer/
  python perception_integration.py

Prerequisites:
  - mock_server.py running: python api/ingestion_server/mock_server.py
  - numpy installed: pip install numpy
"""

import os
import sys
import json
import time
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from hybrid_signal_builder import HybridSignalBuilder
from perception_node import process_signal

ENDPOINT    = "http://localhost:8000/ingest/signal"
HEALTH_URL  = "http://localhost:8000/health"
LOG_FILE    = os.path.join(BASE_DIR, "perception_integration_log.jsonl")

VESSEL_TYPES = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]

lines = []
perception_events = []

def log(msg=""):
    print(msg)
    lines.append(str(msg))

# ─────────────────────────────────────────────────────────────────────────────

log("=" * 65)
log("  SVACS — PHASE 5: PERCEPTION NODE LIVE INTEGRATION")
log(f"  Endpoint : {ENDPOINT}")
log(f"  Run at   : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 65)

# ── Health check ──────────────────────────────────────────────────────────────
log("\n  [HEALTH CHECK]")
try:
    h = requests.get(HEALTH_URL, timeout=3).json()
    log(f"  Status          : {h.get('status')}")
    log(f"  Chunks received : {h.get('chunks_received')}")
    log(f"  Chunks rejected : {h.get('chunks_rejected')}")
except Exception as e:
    log(f"  [ERROR] Cannot reach server: {e}")
    log("  → Start mock_server.py first: python api/ingestion_server/mock_server.py")
    sys.exit(1)

# ── Run 3 chunks per vessel type (15 total) ───────────────────────────────────
log(f"\n  Sending 3 chunks per vessel type (15 total)...")
log(f"  {'─' * 60}")

builder = HybridSignalBuilder(sample_rate=4000, duration=1.0)
passed  = 0
failed  = 0

for vtype in VESSEL_TYPES:
    for i in range(3):
        chunk = builder.build(vtype)

        # Step 1: POST to ingestion server
        try:
            r    = requests.post(ENDPOINT, json=chunk, timeout=5)
            http_ok = (r.status_code == 200)
            server_trace = r.json().get("trace_id", "")
        except Exception as e:
            log(f"  [{vtype:<16}] chunk {i+1} → HTTP ERROR: {e}")
            failed += 1
            continue

        # Step 2: Run perception node
        perception_event = process_signal(chunk)

        # Step 3: Verify trace_id continuity
        trace_ok = (
            perception_event.get("trace_id") == chunk["trace_id"] == server_trace
        )

        # Step 4: Log result
        has_all = all(k in perception_event for k in [
            "trace_id", "vessel_type", "confidence_score",
            "dominant_freq_hz", "anomaly_flag"
        ])
        no_error = "error" not in perception_event
        ok = http_ok and trace_ok and has_all and no_error

        if ok:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        log(
            f"  [{vtype:<16}] #{i+1} "
            f"HTTP={r.status_code} | "
            f"vessel={perception_event.get('vessel_type'):<12} | "
            f"conf={perception_event.get('confidence_score'):.3f} | "
            f"anomaly={perception_event.get('anomaly_flag')} | "
            f"trace={'OK' if trace_ok else 'MISMATCH'} | "
            f"{status}"
        )

        # Save perception event with trace proof
        perception_events.append({
            "input_trace_id":      chunk["trace_id"],
            "server_trace_id":     server_trace,
            "output_trace_id":     perception_event.get("trace_id"),
            "trace_continuity":    trace_ok,
            "perception_event":    perception_event,
            "input_vessel_type":   vtype,
            "http_status":         r.status_code,
        })

        time.sleep(0.03)  # 30ms between chunks

# ── Summary ───────────────────────────────────────────────────────────────────
log(f"\n{'=' * 65}")
log("  INTEGRATION SUMMARY")
log(f"{'=' * 65}")
log(f"  Chunks sent      : {passed + failed}")
log(f"  Passed           : {passed}")
log(f"  Failed           : {failed}")

# Show trace continuity proof
trace_matches = sum(1 for e in perception_events if e["trace_continuity"])
log(f"  Trace continuity : {trace_matches}/{len(perception_events)} (input = server = output)")

# Verify required vessel types captured
vessels_found = set(e["perception_event"].get("vessel_type") for e in perception_events)
anomalies     = [e for e in perception_events if e["perception_event"].get("anomaly_flag")]
log(f"  Vessel types     : {sorted(vessels_found)}")
log(f"  Anomalies flagged: {len(anomalies)}")

if passed == 15 and trace_matches == 15:
    log("\n  [PASS] FULL PIPELINE INTEGRATION COMPLETE")
    log("  signal_chunk → mock_server → perception_node → perception_event")
    log("  trace_id preserved end-to-end across all 15 chunks")
else:
    log(f"\n  [PARTIAL] {failed} chunk(s) failed — review above")

log("=" * 65)

# ── Save perception events log ────────────────────────────────────────────────
with open(LOG_FILE, "w", encoding="utf-8") as f:
    for event in perception_events:
        f.write(json.dumps(event) + "\n")

print(f"\n[LOG SAVED] → {LOG_FILE}")
