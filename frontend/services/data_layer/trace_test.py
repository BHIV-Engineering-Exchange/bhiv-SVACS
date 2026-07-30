"""
SVACS — trace_test.py
======================
PHASE 3 |  Trace ID Continuity Test

Sends 10 chunks (2 per vessel type) to /ingest/signal.
Verifies that trace_id sent == trace_id returned in HTTP response.
Proves the server never drops, modifies, or replaces the trace_id.

Run from: services/data_layer/
  python trace_test.py
"""

import os, sys, json, time, re
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from hybrid_signal_builder import HybridSignalBuilder

ENDPOINT  = "http://localhost:8000/ingest/signal"
LOG_FILE  = os.path.join(BASE_DIR, "trace_test_log.txt")
UUID_RE   = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.I
)

lines = []

def log(msg=""):
    print(msg)
    lines.append(str(msg))

builder     = HybridSignalBuilder(4000, 1.0)
vtypes      = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]
sent_traces = []
results     = []

log("=" * 65)
log("  SVACS — PHASE 3: TRACE ID CONTINUITY TEST")
log(f"  Endpoint : {ENDPOINT}")
log(f"  Run at   : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 65)

for vtype in vtypes:
    for repeat in range(2):   # 2 chunks per vessel = 10 total
        chunk = builder.build(vtype)
        sent_tid = chunk["trace_id"]
        sent_traces.append(sent_tid)

        try:
            r = requests.post(ENDPOINT, json=chunk, timeout=5)
            resp = r.json()
            returned_tid = resp.get("trace_id", "MISSING")

            match   = (returned_tid == sent_tid)
            valid   = bool(UUID_RE.match(returned_tid)) if returned_tid != "MISSING" else False
            status  = "PASS" if (match and r.status_code == 200) else "FAIL"

            log(f"\n  [{vtype.upper()} #{repeat+1}]")
            log(f"    HTTP status  : {r.status_code}")
            log(f"    sent         : {sent_tid}")
            log(f"    returned     : {returned_tid}")
            log(f"    match        : {'YES ' if match else 'NO  — TRACE CORRUPTED'}")
            log(f"    UUID4 valid  : {'YES' if valid else 'NO'}")
            log(f"    result       : {status}")

        except requests.exceptions.ConnectionError:
            log(f"\n  [{vtype.upper()} #{repeat+1}] FAIL — Server not reachable at {ENDPOINT}")
            log("  Make sure mock_server.py is running.")
            status       = "FAIL"
            returned_tid = "CONNECTION_ERROR"
            match        = False

        results.append({
            "vessel_type": vtype,
            "repeat":      repeat + 1,
            "sent":        sent_tid,
            "returned":    returned_tid,
            "match":       match,
            "status":      status
        })

# ── Uniqueness check ──────────────────────────────────────────────────────────
unique_count  = len(set(sent_traces))
all_unique    = (unique_count == len(sent_traces))
all_pass      = all(r["status"] == "PASS" for r in results)
passed        = sum(1 for r in results if r["status"] == "PASS")

log(f"\n{'=' * 65}")
log("  TRACE CONTINUITY SUMMARY")
log(f"{'=' * 65}")
log(f"  Total chunks sent     : {len(sent_traces)}")
log(f"  trace_id matches      : {passed}/{len(results)}")
log(f"  All trace_ids unique  : {'YES ' if all_unique else 'NO '} ({unique_count} unique out of {len(sent_traces)})")

if all_pass and all_unique:
    log("\n  [PASS] TRACE CONTINUITY CONFIRMED")
    log("  Every trace_id was preserved exactly through ingestion.")
    log("  No drops. No overwrites. No duplicates.")
else:
    log("\n  [FAIL] TRACE ISSUES DETECTED — review above")

log(f"\n  Log saved: {LOG_FILE}")
log("=" * 65)

# ── Save log ──────────────────────────────────────────────────────────────────
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

json_path = os.path.join(BASE_DIR, "trace_test_results.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump({
        "run_at":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_sent":   len(sent_traces),
        "passed":       passed,
        "all_unique":   all_unique,
        "overall_pass": all_pass and all_unique,
        "results":      results
    }, f, indent=2)

print(f"[JSON SAVED] → {json_path}")