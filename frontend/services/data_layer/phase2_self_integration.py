"""
SVACS — phase2_self_integration.py
==================================
Simulates what Acoustic Node will do when it consumes signal chunks.
Runs all 5 vessel types, validates field access, classifies signals,
and saves results to phase2_integration_log.txt

Run from: services/data_layer/
  python phase2_self_integration.py
"""

import os
import sys
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "utils"))

from hybrid_signal_builder import HybridSignalBuilder
import signal_utils as utils

LOG_FILE = os.path.join(BASE_DIR, "phase2_integration_log.txt")
lines    = []


def log(msg=""):
    print(msg)
    lines.append(msg)


# ── Header ────────────────────────────────────────────────────────────────────

log("=" * 65)
log("  SVACS — PHASE 2 SELF-SIMULATED INTEGRATION TEST")
log(f"  Run at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("  Simulating: Acoustic Node consuming signal chunks")
log("=" * 65)

builder  = HybridSignalBuilder(4000, 1.0)
vtypes   = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]
all_pass = True
results  = []


for vtype in vtypes:
    log(f"\n{'─'*65}")
    log(f"  Vessel Type : {vtype.upper()}")
    chunk  = builder.build(vtype)
    errors = []

    # ── CHECK 1: Required field access (simulates Acoustic Node parser) ───────
    for field in ["samples", "vessel_type", "trace_id", "sample_rate",
                  "timestamp", "expected_label", "snr_db"]:
        if field not in chunk:
            errors.append(f"MISSING FIELD: {field}")

    # ── CHECK 2: Sample count ─────────────────────────────────────────────────
    n = len(chunk.get("samples", []))
    if n != 4000:
        errors.append(f"SAMPLE COUNT WRONG: expected 4000, got {n}")

    # ── CHECK 3: trace_id format ──────────────────────────────────────────────
    import re
    UUID_RE = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        re.I
    )
    tid = chunk.get("trace_id", "")
    if not UUID_RE.match(tid):
        errors.append(f"TRACE_ID INVALID FORMAT: {tid}")

    # ── CHECK 4: anomaly handling — metadata.freq_hz can be "mixed" ──────────
    freq_hz = chunk.get("metadata", {}).get("freq_hz", None)
    freq_ok = isinstance(freq_hz, (int, float)) or freq_hz == "mixed"
    if not freq_ok:
        errors.append(f"freq_hz unexpected value: {freq_hz}")

    # ── CHECK 5: anomaly_flag correct ─────────────────────────────────────────
    anomaly_flag = chunk.get("expected_label", {}).get("anomaly_flag", None)
    expected_anomaly = (vtype == "anomaly")
    if anomaly_flag != expected_anomaly:
        errors.append(f"ANOMALY_FLAG WRONG: expected {expected_anomaly}, got {anomaly_flag}")

    # ── CHECK 6: rule-based classification (simulates downstream classifier) ──
    classification = utils.rule_classify(chunk)

    # ── Print results ─────────────────────────────────────────────────────────
    log(f"  trace_id     : {tid[:8]}...")
    log(f"  samples      : {n} floats ({'OK' if n == 4000 else 'FAIL'})")
    log(f"  sample_rate  : {chunk.get('sample_rate')}")
    log(f"  snr_db       : {chunk.get('snr_db')} dB")
    log(f"  freq_hz      : {freq_hz} ({'OK' if freq_ok else 'FAIL'})")
    log(f"  anomaly_flag : {anomaly_flag} (expected: {expected_anomaly}) "
        f"{'OK' if anomaly_flag == expected_anomaly else 'FAIL'}")
    log(f"  ── Rule Classifier Output ──")
    log(f"     predicted  : {classification['predicted_type']}")
    log(f"     confidence : {classification['confidence']}")
    log(f"     dom_freq   : {classification['dominant_freq_hz']:.1f} Hz")
    log(f"     anomaly    : {classification['anomaly']}")

    if errors:
        all_pass = False
        log(f"\n  [FAIL] {len(errors)} issue(s) found:")
        for e in errors:
            log(f"     {e}")
        status = "FAIL"
    else:
        log(f"\n  [PASS] All checks passed — chunk is parsable and classifiable")
        status = "PASS"

    results.append({
        "vessel_type":      vtype,
        "status":           status,
        "trace_id":         tid,
        "sample_count":     n,
        "anomaly_flag":     anomaly_flag,
        "predicted_type":   classification["predicted_type"],
        "confidence":       classification["confidence"],
        "dominant_freq_hz": round(classification["dominant_freq_hz"], 2),
        "errors":           errors
    })


# ── Summary ───────────────────────────────────────────────────────────────────

log(f"\n{'=' * 65}")
log("  SUMMARY")
log(f"{'=' * 65}")
log(f"  {'VESSEL TYPE':<20} {'STATUS':<8} {'PREDICTED':<18} {'CONF':<8} ANOMALY")
log(f"  {'─'*60}")

for r in results:
    log(
        f"  {r['vessel_type']:<20} {r['status']:<8} "
        f"{r['predicted_type']:<18} {str(r['confidence']):<8} "
        f"{r['anomaly_flag']}"
    )

passed = sum(1 for r in results if r["status"] == "PASS")
log(f"\n  Result : {passed}/5 vessel types passed all checks")

if all_pass:
    log("\n   SIGNAL LAYER IS READY FOR ACOUSTIC NODE CONSUMPTION")
    log("     No schema or parsing issues found.")
    log("     Downstream team can integrate without signal-side changes.")
else:
    log("\n    SOME CHECKS FAILED — review errors above before handoff")

log(f"\n  Log saved to: {LOG_FILE}")
log("=" * 65)


# ── Save log file ─────────────────────────────────────────────────────────────

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

# ── Also save structured JSON results ────────────────────────────────────────

json_log = os.path.join(BASE_DIR, "phase2_integration_results.json")
with open(json_log, "w", encoding="utf-8") as f:
    json.dump({
        "run_at":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall_pass": all_pass,
        "total_passed": passed,
        "total_tested": len(results),
        "results":      results
    }, f, indent=2)

print(f"[JSON SAVED] → {json_log}")
