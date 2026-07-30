"""
SVACS — test_failures.py
=========================
Tests edge cases against /ingest/signal.
Now checks CORRECT expected HTTP status codes:
  - Bad JSON        → 400
  - Missing fields  → 422
  - Empty samples   → 422
  - Invalid vessel  → 422
  - Valid chunk     → 200

Results are printed AND saved to test_failures_log.txt
"""

import requests
import json
import os
import sys
import time

#  Add data_layer to path for imports 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "utils"))

BASE_URL  = "http://localhost:8000/ingest/signal"
LOG_FILE  = os.path.join(BASE_DIR, "test_failures_log.txt")

results = []


def log(msg: str):
    """Print and buffer for file write."""
    print(msg)
    results.append(msg)


def check(label: str, expected_status: int, actual_status: int, resp_body: dict):
    match = (actual_status == expected_status)
    icon  = "PASS" if match else "FAIL"
    msg   = (
        f"[{icon}] {label}\n"
        f"       expected HTTP {expected_status} | got HTTP {actual_status}\n"
        f"       response: {resp_body}"
    )
    log(msg)
    return match


#  Test runner 

log("=" * 60)
log("SVACS — test_failures.py")
log(f"Target : {BASE_URL}")
log(f"Time   : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 60 + "\n")


#  TEST 1: Malformed / empty body (bad JSON) → expect 400 
log(" TEST 1: Bad JSON body ")
try:
    import urllib.request as ureq
    req = ureq.Request(
        BASE_URL,
        data=b"NOT JSON {{{",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with ureq.urlopen(req, timeout=3) as resp:
        body = json.loads(resp.read())
        check("Bad JSON", 400, resp.status, body)
except Exception as e:
    # urllib raises on 4xx — extract code from error
    code_str = str(e)
    if "400" in code_str:
        log(f"[PASS] Bad JSON → HTTP 400 (urllib raised: {e})")
    else:
        log(f"[FAIL] Bad JSON → unexpected error: {e}")


#  TEST 2: Missing required fields → expect 422 
log("\n TEST 2: Missing required fields ")
r = requests.post(BASE_URL, json={"trace_id": "abc123"}, timeout=3)
check("Missing fields", 422, r.status_code, r.json())


#  TEST 3: Empty samples array → expect 422 
log("\n TEST 3: Empty samples array ")
r = requests.post(BASE_URL, json={
    "trace_id":    "00000000-0000-4000-8000-000000000001",
    "timestamp":   time.time(),
    "samples":     [],
    "sample_rate": 4000,
    "vessel_type": "cargo"
}, timeout=3)
check("Empty samples", 422, r.status_code, r.json())


#  TEST 4: Invalid vessel_type → expect 422 
log("\n TEST 4: Invalid vessel_type ")
r = requests.post(BASE_URL, json={
    "trace_id":    "00000000-0000-4000-8000-000000000002",
    "timestamp":   time.time(),
    "samples":     [0.1] * 4000,
    "sample_rate": 4000,
    "vessel_type": "UNKNOWN_VESSEL"
}, timeout=3)
check("Invalid vessel_type", 422, r.status_code, r.json())


#  TEST 5: Invalid (non-UUID) trace_id → expect 422 
log("\n TEST 5: Non-UUID trace_id ")
r = requests.post(BASE_URL, json={
    "trace_id":    "not-a-uuid",
    "timestamp":   time.time(),
    "samples":     [0.1] * 4000,
    "sample_rate": 4000,
    "vessel_type": "cargo"
}, timeout=3)
check("Non-UUID trace_id", 422, r.status_code, r.json())


#  TEST 6: Valid full chunk → expect 200 
log("\n TEST 6: Valid chunk (cargo) → expect 200 ")
try:
    from hybrid_signal_builder import HybridSignalBuilder
    builder = HybridSignalBuilder(4000, 1.0)
    chunk = builder.build("cargo")
    r = requests.post(BASE_URL, json=chunk, timeout=5)
    check("Valid cargo chunk", 200, r.status_code, r.json())
except ImportError:
    log("[SKIP] HybridSignalBuilder not importable from this path — skipped")


#  TEST 7: Health check 
log("\n TEST 7: Health endpoint ")
r = requests.get("http://localhost:8000/health", timeout=3)
body = r.json()
log(f"[INFO] Health: {body}")
if r.status_code == 200 and body.get("status") == "alive":
    log(f"[PASS] Health check → alive | received={body['chunks_received']} rejected={body['chunks_rejected']}")
else:
    log(f"[FAIL] Health check unexpected response")


#  Summary 
log("\n" + "=" * 60)
log("FAILURE HANDLING TEST COMPLETE")
log("=" * 60)

# Write to file
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(results) + "\n")

print(f"\n[LOG SAVED] → {LOG_FILE}")