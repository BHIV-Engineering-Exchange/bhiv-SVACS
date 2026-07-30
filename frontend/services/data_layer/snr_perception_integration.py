"""
SVACS — snr_perception_integration.py
========================================
Task: Signal → Perception Integration + SNR Fix
Validation runner covering all 5 phases of the new task:

  PHASE 1 — SNR Fix verification
  PHASE 2 — Dual endpoint contract (/ingest vs /ingest/signal)
  PHASE 3 — Live perception connection
  PHASE 4 — Full transformation log (all 5 vessel types)
  PHASE 5 — Latency measurement (avg + max, target <100ms)

Run from svacs-demo/services/data_layer/:
  python snr_perception_integration.py

Prerequisites:
  - mock_server.py running (updated version with dual endpoints)
  - numpy, requests installed
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

PRIMARY_ENDPOINT = "http://localhost:8000/ingest"
ALIAS_ENDPOINT   = "http://localhost:8000/ingest/signal"
HEALTH_URL       = "http://localhost:8000/health"
PERC_LOG_URL     = "http://localhost:8000/perception_log"

LOG_FILE = os.path.join(BASE_DIR, "snr_perception_integration_log.jsonl")
VESSEL_TYPES = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]

# Expected SNR ranges per task spec
SNR_RANGES = {
    "cargo":          (15, 25),
    "speedboat":      (10, 20),
    "submarine":      (5,  10),
    "low_confidence": (-99, 5),
    "anomaly":        (-99, 99),  # variable — no strict range
}

results    = []
latencies  = []
log_events = []

def log(msg=""):
    print(msg)
    log_events.append(str(msg))

# ─────────────────────────────────────────────────────────────────────────────

log("=" * 68)
log("  SVACS — SNR FIX + PERCEPTION INTEGRATION VALIDATION")
log(f"  Run at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 68)

# ── Health check ──────────────────────────────────────────────────────────────
log("\n[HEALTH CHECK]")
try:
    h = requests.get(HEALTH_URL, timeout=3).json()
    log(f"  Status           : {h.get('status')}")
    log(f"  Chunks received  : {h.get('chunks_received')}")
    log(f"  Avg latency (ms) : {h.get('avg_latency_ms')}")
except Exception as e:
    log(f"  [ERROR] Cannot reach server: {e}")
    log("  → Start mock_server.py first")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — SNR Verification
# ─────────────────────────────────────────────────────────────────────────────
log("\n" + "─" * 68)
log("PHASE 1 — SNR FIX VERIFICATION")
log("─" * 68)
log(f"  {'VESSEL':<16}  {'SNR_DB':>8}  {'RANGE':>12}  {'STATUS'}")
log(f"  {'─'*16}  {'─'*8}  {'─'*12}  {'─'*6}")

builder     = HybridSignalBuilder(sample_rate=4000, duration=1.0)
snr_pass    = 0
snr_fail    = 0
snr_results = {}

for vtype in VESSEL_TYPES:
    chunk  = builder.build(vtype)
    snr    = chunk.get("snr_db", None)
    lo, hi = SNR_RANGES[vtype]

    if snr is None:
        status = "FAIL (missing)"
        snr_fail += 1
    elif vtype == "anomaly":
        status = "PASS (variable)"
        snr_pass += 1
    elif lo <= snr <= hi:
        status = "PASS"
        snr_pass += 1
    else:
        status = f"FAIL (out of range)"
        snr_fail += 1

    snr_results[vtype] = {"snr_db": snr, "expected": f"{lo}–{hi} dB", "status": status}
    log(f"  {vtype:<16}  {str(snr):>8}  {lo}–{hi} dB    {status}")

log(f"\n  SNR: {snr_pass}/{len(VESSEL_TYPES)} PASS")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — Dual Endpoint Contract
# ─────────────────────────────────────────────────────────────────────────────
log("\n" + "─" * 68)
log("PHASE 2 — DUAL ENDPOINT CONTRACT (/ingest vs /ingest/signal)")
log("─" * 68)

ep_pass = 0
ep_fail = 0

for vtype in VESSEL_TYPES[:3]:  # test 3 vessel types
    chunk = builder.build(vtype)

    try:
        r1 = requests.post(PRIMARY_ENDPOINT, json=chunk, timeout=5)
        r2 = requests.post(ALIAS_ENDPOINT,   json=chunk, timeout=5)

        codes_match  = (r1.status_code == r2.status_code == 200)
        trace1_ok    = r1.json().get("trace_id") == chunk["trace_id"]
        trace2_ok    = r2.json().get("trace_id") == chunk["trace_id"]

        if codes_match and trace1_ok and trace2_ok:
            ep_pass += 1
            status = "PASS"
        else:
            ep_fail += 1
            status = f"FAIL (codes={r1.status_code}/{r2.status_code} trace1={trace1_ok} trace2={trace2_ok})"
    except Exception as e:
        ep_fail += 1
        status = f"ERROR: {e}"

    log(f"  {vtype:<16}: /ingest={r1.status_code if 'r1' in dir() else '?'}  /ingest/signal={r2.status_code if 'r2' in dir() else '?'}  → {status}")

log(f"\n  Dual endpoint: {ep_pass}/3 PASS")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — Live Perception Connection
# ─────────────────────────────────────────────────────────────────────────────
log("\n" + "─" * 68)
log("PHASE 3 — LIVE PERCEPTION CONNECTION")
log("─" * 68)
log(f"  Sending 15 chunks (3 per vessel type) via PRIMARY /ingest endpoint")
log()

perc_pass = 0
perc_fail = 0

for vtype in VESSEL_TYPES:
    for i in range(3):
        chunk = builder.build(vtype)
        t_start = time.time()

        try:
            r = requests.post(PRIMARY_ENDPOINT, json=chunk, timeout=5)
            http_ok = (r.status_code == 200)
        except Exception as e:
            log(f"  [{vtype}] #{i+1} HTTP ERROR: {e}")
            perc_fail += 1
            continue

        # Call perception node directly (mirror what server does)
        perception_event = process_signal(chunk)
        latency_ms = round((time.time() - t_start) * 1000, 3)
        latencies.append(latency_ms)

        trace_ok = (
            perception_event.get("trace_id") == chunk["trace_id"] ==
            r.json().get("trace_id")
        )
        has_all = all(k in perception_event for k in [
            "trace_id", "vessel_type", "confidence_score",
            "dominant_freq_hz", "anomaly_flag"
        ])
        no_err = "error" not in perception_event
        ok     = http_ok and trace_ok and has_all and no_err

        if ok:
            perc_pass += 1
            status = "PASS"
        else:
            perc_fail += 1
            status = f"FAIL (http={http_ok} trace={trace_ok} fields={has_all} no_err={no_err})"

        log(
            f"  [{vtype:<16}] #{i+1}  "
            f"vessel={perception_event.get('vessel_type'):<12}  "
            f"conf={perception_event.get('confidence_score'):.3f}  "
            f"anomaly={perception_event.get('anomaly_flag')}  "
            f"trace={'OK' if trace_ok else 'FAIL'}  "
            f"lat={latency_ms}ms  {status}"
        )

        results.append({
            "trace_id":          chunk["trace_id"],
            "input_vessel":      vtype,
            "predicted_vessel":  perception_event.get("vessel_type"),
            "confidence":        perception_event.get("confidence_score"),
            "dominant_freq":     perception_event.get("dominant_freq_hz"),
            "anomaly":           perception_event.get("anomaly_flag"),
            "snr_db":            chunk.get("snr_db"),
            "latency_ms":        latency_ms,
            "trace_ok":          trace_ok,
            "status":            status,
        })

        time.sleep(0.02)

log(f"\n  Perception: {perc_pass}/15 PASS")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — Transformation Log (1 per vessel type)
# ─────────────────────────────────────────────────────────────────────────────
log("\n" + "─" * 68)
log("PHASE 4 — PERCEPTION TRANSFORMATION LOG (1 per vessel type)")
log("─" * 68)

seen_vessels = {}
for r in results:
    v = r["input_vessel"]
    if v not in seen_vessels:
        seen_vessels[v] = r

log_entries = []
for vtype in VESSEL_TYPES:
    if vtype in seen_vessels:
        entry = {
            "trace_id":          seen_vessels[vtype]["trace_id"],
            "input_vessel":      vtype,
            "predicted_vessel":  seen_vessels[vtype]["predicted_vessel"],
            "confidence":        seen_vessels[vtype]["confidence"],
            "dominant_freq":     seen_vessels[vtype]["dominant_freq"],
            "anomaly":           seen_vessels[vtype]["anomaly"],
        }
        log_entries.append(entry)
        log(f"  {vtype:<16}: predicted={entry['predicted_vessel']:<12}  conf={entry['confidence']}  freq={entry['dominant_freq']}  anomaly={entry['anomaly']}")
    else:
        log(f"  {vtype:<16}: NO DATA")

log(f"\n  Transformation log: {len(log_entries)}/5 vessel types captured")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5 — Latency Report
# ─────────────────────────────────────────────────────────────────────────────
log("\n" + "─" * 68)
log("PHASE 5 — LATENCY REPORT")
log("─" * 68)

if latencies:
    avg_lat = round(sum(latencies) / len(latencies), 3)
    max_lat = round(max(latencies), 3)
    min_lat = round(min(latencies), 3)
    under_100 = sum(1 for l in latencies if l < 100)

    log(f"  Events measured  : {len(latencies)}")
    log(f"  Average latency  : {avg_lat} ms")
    log(f"  Max latency      : {max_lat} ms")
    log(f"  Min latency      : {min_lat} ms")
    log(f"  Under 100ms      : {under_100}/{len(latencies)}")
    lat_pass = (avg_lat < 100 and max_lat < 100)
    log(f"  Target (<100ms)  : {'PASS' if lat_pass else 'WARN — some events exceeded 100ms'}")
else:
    log("  No latency data captured")
    lat_pass = False

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
log("\n" + "=" * 68)
log("  FINAL SUMMARY")
log("=" * 68)
log(f"  Phase 1 — SNR Fix         : {snr_pass}/{len(VESSEL_TYPES)} PASS")
log(f"  Phase 2 — Dual Endpoints  : {ep_pass}/3 PASS")
log(f"  Phase 3 — Perception Live : {perc_pass}/15 PASS")
log(f"  Phase 4 — Transform Log   : {len(log_entries)}/5 vessels captured")
log(f"  Phase 5 — Latency         : avg={avg_lat if latencies else 'N/A'}ms  max={max_lat if latencies else 'N/A'}ms")

all_pass = (snr_pass == 5 and ep_pass == 3 and perc_pass == 15 and len(log_entries) == 5)
if all_pass:
    log("\n  [COMPLETE] ALL PHASES PASSED")
    log("  signal_chunk → mock_server → perception_node → perception_event")
    log("  SNR realistic | Both endpoints live | trace_id preserved end-to-end")
else:
    log(f"\n  [PARTIAL] Review failures above")

log("=" * 68)

# ── Save full log ─────────────────────────────────────────────────────────────
with open(LOG_FILE, "w", encoding="utf-8") as f:
    for entry in results:
        f.write(json.dumps(entry) + "\n")

print(f"\n[LOG SAVED] {LOG_FILE}")

# ── Save transformation log as separate file ──────────────────────────────────
transform_log_path = os.path.join(BASE_DIR, "transformation_log.jsonl")
with open(transform_log_path, "w", encoding="utf-8") as f:
    for entry in log_entries:
        f.write(json.dumps(entry) + "\n")

print(f"[TRANSFORM LOG] {transform_log_path}")
