"""
SVACS — day5_final_run.py
==========================
PHASE 5 | Full Pipeline Dry Run

Sends the complete demo stream (all 5 scenarios) to the server
and captures results to phase5_dry_run_log.txt.

Also checks /health endpoint before and after.

Run from: services/data_layer/
  python phase5_final_run.py

Prerequisites:
  - mock_server.py must be running in another terminal
  - python api/ingestion_server/mock_server.py

Output: phase5_dry_run_log.txt
"""

import os, sys, json, time
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import requests
from hybrid_signal_builder import HybridSignalBuilder

ENDPOINT    = "http://localhost:8000/ingest/signal"
HEALTH_URL  = "http://localhost:8000/health"
LOG_FILE    = os.path.join(BASE_DIR, "phase5_dry_run_log.txt")

VESSELS = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]

lines = []
def log(msg=""):
    print(msg)
    lines.append(str(msg))

log("=" * 65)
log("  SVACS — PHASE 5: FULL PIPELINE DRY RUN")
log(f"  Endpoint : {ENDPOINT}")
log(f"  Run at   : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 65)

# ── Health check BEFORE ───────────────────────────────────────────────────────
log("\n  [HEALTH CHECK — BEFORE]")
try:
    h = requests.get(HEALTH_URL, timeout=3).json()
    log(f"  Status          : {h.get('status')}")
    log(f"  Chunks received : {h.get('chunks_received')}")
    log(f"  Chunks rejected : {h.get('chunks_rejected')}")
except Exception as e:
    log(f"  [ERROR] Could not reach server: {e}")
    log("  Make sure mock_server.py is running in another terminal.")
    sys.exit(1)

# ── Send 3 chunks per vessel type (15 total) ──────────────────────────────────
log(f"\n  Sending 3 chunks per vessel (15 total)...")
log(f"  {'─' * 60}")

builder    = HybridSignalBuilder(4000, 1.0)
passed     = 0
failed     = 0
all_traces = []

for vtype in VESSELS:
    for i in range(3):
        chunk = builder.build(vtype)
        try:
            r    = requests.post(ENDPOINT, json=chunk, timeout=5)
            resp = r.json()
            ok   = (r.status_code == 200)
            tid_ok = (resp.get("trace_id") == chunk["trace_id"])

            status = "OK" if (ok and tid_ok) else "FAIL"
            if ok and tid_ok:
                passed += 1
            else:
                failed += 1

            log(
                f"  [{vtype:<16}] chunk {i+1} "
                f"-> HTTP {r.status_code} | "
                f"trace={'match' if tid_ok else 'MISMATCH'} | "
                f"anomaly={chunk.get('expected_label',{}).get('anomaly_flag',False)} | "
                f"{status}"
            )
            all_traces.append(chunk["trace_id"])

        except Exception as e:
            failed += 1
            log(f"  [{vtype:<16}] chunk {i+1} -> ERROR: {e}")

# ── Health check AFTER ────────────────────────────────────────────────────────
log(f"\n  [HEALTH CHECK — AFTER]")
try:
    h = requests.get(HEALTH_URL, timeout=3).json()
    log(f"  Status          : {h.get('status')}")
    log(f"  Chunks received : {h.get('chunks_received')}")
    log(f"  Chunks rejected : {h.get('chunks_rejected')}")
    log(f"  Log file        : {h.get('log_file')}")
    log(f"  Trace log       : {h.get('trace_log')}")
except Exception as e:
    log(f"  [ERROR] Health check failed: {e}")

# ── Uniqueness check ──────────────────────────────────────────────────────────
unique     = len(set(all_traces)) == len(all_traces)
overall_ok = (failed == 0) and unique

log(f"\n{'=' * 65}")
log("  DRY RUN SUMMARY")
log(f"{'=' * 65}")
log(f"  Chunks sent     : {passed + failed}")
log(f"  Passed          : {passed}")
log(f"  Failed          : {failed}")
log(f"  Unique trace_ids: {'YES' if unique else 'NO — DUPLICATES FOUND'}")

if overall_ok:
    log("\n  [PASS] FULL PIPELINE DRY RUN COMPLETE")
    log("  Server is stable. All chunks accepted. All traces unique.")
else:
    log(f"\n  [FAIL] Issues found — review above")

log("=" * 65)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\n[LOG SAVED] -> {LOG_FILE}")
