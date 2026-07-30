"""
SVACS — trace_break_test.py
============================
PHASE 3 |  Trace Break / Edge Case Testing

Tests what happens when trace_id is:
  - missing entirely        → expect HTTP 422
  - an empty string         → expect HTTP 422
  - not UUID4 format        → expect HTTP 422
  - a known fixed value     → expect HTTP 200, returned unchanged

Run from: services/data_layer/
  python trace_break_test.py
"""

import os, sys, json, time, copy
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from hybrid_signal_builder import HybridSignalBuilder

ENDPOINT = "http://localhost:8000/ingest/signal"
builder  = HybridSignalBuilder(4000, 1.0)
lines    = []

def log(msg=""):
    print(msg)
    lines.append(str(msg))

def fresh_chunk():
    """Always returns a deep copy so mutations don't bleed between tests."""
    return copy.deepcopy(builder.build("cargo"))

log("=" * 65)
log("  SVACS — PHASE 3: TRACE BREAK TEST")
log(f"  Run at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 65)

FIXED_UUID = "00000000-0000-4000-8000-000000000001"

tests = [
    {
        "name":    "Missing trace_id",
        "chunk":   lambda: {k: v for k, v in fresh_chunk().items() if k != "trace_id"},
        "expect":  422,
    },
    {
        "name":    "Empty string trace_id",
        "chunk":   lambda: {**fresh_chunk(), "trace_id": ""},
        "expect":  422,
    },
    {
        "name":    "Non-UUID trace_id",
        "chunk":   lambda: {**fresh_chunk(), "trace_id": "not-a-uuid"},
        "expect":  422,
    },
    {
        "name":    "Known fixed trace_id (preserved?)",
        "chunk":   lambda: {**fresh_chunk(), "trace_id": FIXED_UUID},
        "expect":  200,
    },
]

all_pass = True

for test in tests:
    chunk         = test["chunk"]()
    expected_code = test["expect"]
    log(f"\n  Test  : {test['name']}")

    try:
        r    = requests.post(ENDPOINT, json=chunk, timeout=5)
        code = r.status_code

        # Safe body parse — some rejection responses may have empty body
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:120] if r.text else "(empty body)"}

        # Determine pass/fail
        if code == expected_code:
            if expected_code == 200:
                returned  = body.get("trace_id", "")
                preserved = (returned == FIXED_UUID)
                detail    = f"returned={returned[:20]}... | preserved={'YES ' if preserved else 'NO '}"
                status    = "PASS" if preserved else "FAIL — trace_id not preserved"
                if not preserved:
                    all_pass = False
            else:
                reason = body.get("reason", body.get("detail", str(body))[:80])
                detail = f"reason={reason}"
                status = "PASS"
        else:
            detail   = f"body={str(body)[:80]}"
            status   = f"FAIL (got HTTP {code}, expected {expected_code})"
            all_pass = False

    except requests.exceptions.ConnectionError:
        code     = "N/A"
        detail   = "Server not reachable — is mock_server.py running?"
        status   = "FAIL"
        all_pass = False

    log(f"  HTTP  : {code} (expected {expected_code})")
    log(f"  Detail: {detail}")
    log(f"  Result: {status}")

log(f"\n{'=' * 65}")
if all_pass:
    log("  [PASS] All break tests passed.")
    log("  Server correctly rejects bad trace_ids and preserves valid ones.")
else:
    log("  [FAIL] Some tests failed — review above.")
log("=" * 65)

out = os.path.join(BASE_DIR, "trace_break_test_log.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\n[LOG SAVED] → {out}")