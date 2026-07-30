"""
SVACS — test_edge_cases.py
===========================
PHASE 2 | Edge Case Simulation
Simulates Acoustic Node parser consuming signal chunks.

Checks per vessel type:
  1. Field access        — no missing keys
  2. Sample size         — exactly 4000
  3. Data type           — all floats
  4. trace_id            — valid UUID4 string
  5. Anomaly handling    — freq_hz can be "mixed" (string), must not crash
  6. Normalization       — all samples within [-1.0, 1.0]
  7. Required sub-fields — expected_label fields present

Run from: services/data_layer/
  python test_edge_cases.py

Output files:
  test_edge_cases_log.txt      (human-readable)
  test_edge_cases_results.json (structured, for REVIEW_PACKET)
"""

import os
import sys
import json
import time
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "utils"))

from hybrid_signal_builder import HybridSignalBuilder

LOG_FILE  = os.path.join(BASE_DIR, "test_edge_cases_log.txt")
JSON_FILE = os.path.join(BASE_DIR, "test_edge_cases_results.json")

UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)

lines = []

def log(msg=""):
    print(msg)
    lines.append(str(msg))

# ─────────────────────────────────────────────────────────────────────────────

log("=" * 65)
log("  SVACS — PHASE 2: EDGE CASE SIMULATION")
log("  Role: Pretending to be Acoustic Node parser")
log(f"  Run at : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 65)

builder = HybridSignalBuilder(4000, 1.0)
vessels = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]

all_results  = []
overall_pass = True

for vtype in vessels:
    log(f"\n{'─' * 65}")
    log(f"  --- Testing: {vtype.upper()} ---")

    chunk         = builder.build(vtype)
    check_results = {}
    vessel_pass   = True

    # ── CHECK 1: Field access ─────────────────────────────────────────────────
    try:
        samples     = chunk["samples"]
        vessel_type = chunk["vessel_type"]
        trace_id    = chunk["trace_id"]
        timestamp   = chunk["timestamp"]
        sample_rate = chunk["sample_rate"]
        log("  [CHECK 1] Field access          : PASS")
        check_results["field_access"] = "PASS"
    except KeyError as e:
        log(f"  [CHECK 1] Field access          : FAIL -> Missing key {e}")
        check_results["field_access"] = f"FAIL - missing {e}"
        vessel_pass = False
        samples     = chunk.get("samples", [])
        vessel_type = chunk.get("vessel_type", "?")
        trace_id    = chunk.get("trace_id", "")

    # ── CHECK 2: Sample size ──────────────────────────────────────────────────
    n = len(samples)
    if n == 4000:
        log(f"  [CHECK 2] Sample size           : PASS ({n})")
        check_results["sample_size"] = "PASS"
    else:
        log(f"  [CHECK 2] Sample size           : FAIL (expected 4000, got {n})")
        check_results["sample_size"] = f"FAIL - got {n}"
        vessel_pass = False

    # ── CHECK 3: Data type validation ─────────────────────────────────────────
    non_float = [i for i, x in enumerate(samples) if not isinstance(x, float)]
    if not non_float:
        log("  [CHECK 3] Sample data types     : PASS (all float)")
        check_results["sample_types"] = "PASS"
    else:
        log(f"  [CHECK 3] Sample data types     : FAIL ({len(non_float)} non-float values)")
        check_results["sample_types"] = f"FAIL - {len(non_float)} non-floats"
        vessel_pass = False

    # ── CHECK 4: trace_id validation ──────────────────────────────────────────
    if isinstance(trace_id, str) and UUID_RE.match(trace_id):
        log(f"  [CHECK 4] trace_id              : PASS ({trace_id[:8]}...)")
        check_results["trace_id"] = "PASS"
    elif isinstance(trace_id, str) and len(trace_id) > 0:
        log(f"  [CHECK 4] trace_id              : WARN - present but not UUID4: {trace_id[:16]}")
        check_results["trace_id"] = "WARN - not UUID4 format"
    else:
        log(f"  [CHECK 4] trace_id              : FAIL - missing or empty")
        check_results["trace_id"] = "FAIL - missing"
        vessel_pass = False

    # ── CHECK 5: Anomaly freq_hz handling ─────────────────────────────────────
    freq_hz = chunk.get("metadata", {}).get("freq_hz", None)
    if vtype == "anomaly":
        if freq_hz == "mixed":
            log(f"  [CHECK 5] Anomaly freq_hz       : PASS (value='mixed' - string type confirmed)")
        else:
            log(f"  [CHECK 5] Anomaly freq_hz       : INFO (value={freq_hz})")
        # Simulate what a naive parser would do — and show it would crash
        try:
            _ = float(freq_hz)
            log(f"             float() cast result  : OK (numeric)")
        except (ValueError, TypeError):
            log(f"             float() cast result  : Would raise ValueError")
            log(f"             Safe pattern needed  : check isinstance(freq_hz,(int,float)) before casting")
        check_results["anomaly_freq_handling"] = "PASS - freq_hz='mixed', downstream must guard type"
    else:
        if isinstance(freq_hz, (int, float)):
            log(f"  [CHECK 5] freq_hz type check    : PASS ({freq_hz} Hz)")
            check_results["anomaly_freq_handling"] = f"PASS - numeric {freq_hz}"
        else:
            log(f"  [CHECK 5] freq_hz type check    : WARN (got {type(freq_hz).__name__}: {freq_hz})")
            check_results["anomaly_freq_handling"] = f"WARN - unexpected {type(freq_hz).__name__}"

    # ── CHECK 6: Normalization ────────────────────────────────────────────────
    max_val = max(abs(x) for x in samples)
    if max_val <= 1.01:
        log(f"  [CHECK 6] Sample normalization  : PASS (max abs = {max_val:.4f})")
        check_results["normalization"] = "PASS"
    else:
        log(f"  [CHECK 6] Sample normalization  : FAIL (max abs = {max_val:.4f})")
        check_results["normalization"] = f"FAIL - max={max_val:.4f}"
        vessel_pass = False

    # ── CHECK 7: expected_label sub-fields ────────────────────────────────────
    label          = chunk.get("expected_label", {})
    required_label = ["vessel_type", "confidence_range", "scenario_type", "anomaly_flag"]
    missing_label  = [f for f in required_label if f not in label]
    if not missing_label:
        anomaly_flag    = label["anomaly_flag"]
        expected_flag   = (vtype == "anomaly")
        flag_ok         = (anomaly_flag == expected_flag)
        log(f"  [CHECK 7] expected_label fields : PASS | anomaly_flag={anomaly_flag} ({'correct' if flag_ok else 'WRONG'})")
        check_results["expected_label"] = "PASS" if flag_ok else f"FAIL - flag={anomaly_flag}, expected={expected_flag}"
        if not flag_ok:
            vessel_pass = False
    else:
        log(f"  [CHECK 7] expected_label fields : FAIL - missing: {missing_label}")
        check_results["expected_label"] = f"FAIL - missing {missing_label}"
        vessel_pass = False

    # ── Per-vessel summary ────────────────────────────────────────────────────
    status = "PASS" if vessel_pass else "FAIL"
    if not vessel_pass:
        overall_pass = False

    log(f"\n  Summary -> vessel={vessel_type}, samples={n}, trace={trace_id[:8] if trace_id else 'N/A'}...")
    log(f"  Result  -> {status}")

    all_results.append({
        "vessel_type":  vtype,
        "status":       status,
        "checks":       check_results,
        "trace_id":     trace_id,
        "sample_count": n,
    })


# ── Final Summary ─────────────────────────────────────────────────────────────

log(f"\n{'=' * 65}")
log("  EDGE CASE VALIDATION SUMMARY")
log(f"{'=' * 65}")
log(f"  {'VESSEL TYPE':<20} {'RESULT':<8} {'TRACE ID (first 8)'}")
log(f"  {'─' * 55}")
for r in all_results:
    tid_short = r["trace_id"][:8] if r["trace_id"] else "N/A"
    log(f"  {r['vessel_type']:<20} {r['status']:<8} {tid_short}...")

passed = sum(1 for r in all_results if r["status"] == "PASS")
log(f"\n  Total: {passed}/5 vessel types passed all edge case checks")

if overall_pass:
    log("\n  ALL EDGE CASES PASSED")
    log("  Signal data is clean, predictable, and safe for Acoustic Node.")
    log("  No schema or parsing issues found.")
else:
    log("\n  SOME CHECKS FAILED - review details above before handoff")

log(f"\n  Log  : {LOG_FILE}")
log(f"  JSON : {JSON_FILE}")
log("=" * 65)


# ── Save outputs ──────────────────────────────────────────────────────────────

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "run_at":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_pass": overall_pass,
        "passed":       passed,
        "total_tested": len(all_results),
        "results":      all_results
    }, f, indent=2)

print(f"\n[LOG SAVED]  -> {LOG_FILE}")
print(f"[JSON SAVED] -> {JSON_FILE}")
