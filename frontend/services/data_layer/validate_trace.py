"""
SVACS — validate_trace.py
==========================
PHASE 3 | Automated Trace Log Validator

Reads api/ingestion_server/trace_log.jsonl and confirms:
  1. Every entry has a trace_id
  2. No trace_id is None or "MISSING"
  3. All trace_ids are valid UUID4 format
  4. No duplicate trace_ids (each chunk is unique)
  5. All entries have stage = "signal_ingest"

Note: The fixed test UUID used in trace_break_test.py
(00000000-0000-4000-8000-000000000001) is excluded from the
duplicate check because it is intentionally sent twice during
break testing to verify trace preservation.

Run from: services/data_layer/
  python validate_trace.py
"""

import os, sys, json, re, time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "..", "..", "api", "ingestion_server", "trace_log.jsonl")
OUT_FILE = os.path.join(BASE_DIR, "validate_trace_results.json")
UUID_RE  = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.I
)

# Known test UUIDs sent intentionally by trace_break_test.py
# These are excluded from the duplicate check
TEST_UUIDS = {"00000000-0000-4000-8000-000000000001"}

lines = []
def log(msg=""):
    print(msg)
    lines.append(str(msg))

log("=" * 65)
log("  SVACS — PHASE 3: TRACE LOG VALIDATOR")
log(f"  Reading : {os.path.abspath(LOG_FILE)}")
log(f"  Run at  : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 65)

# ── Load trace_log.jsonl ──────────────────────────────────────────────────────
if not os.path.exists(LOG_FILE):
    log(f"\n  [ERROR] trace_log.jsonl not found at: {os.path.abspath(LOG_FILE)}")
    log("  Make sure mock_server.py is running and has received at least one chunk.")
    sys.exit(1)

entries = []
with open(LOG_FILE, encoding="utf-8") as f:
    for i, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            log(f"  [WARN] Line {i+1} could not be parsed: {e}")

log(f"\n  Total entries read : {len(entries)}")

# ── Run checks ────────────────────────────────────────────────────────────────
errors      = []
seen_traces = {}
skipped_test_uuids = 0

for i, entry in enumerate(entries):
    tid   = entry.get("trace_id", None)
    stage = entry.get("stage", "?")
    vtype = entry.get("vessel_type", "?")

    # Check 1: trace_id exists
    if not tid:
        errors.append(f"  Row {i+1}: trace_id is MISSING or null (vessel={vtype})")
        continue

    # Check 2: valid UUID4 format
    if not UUID_RE.match(tid):
        errors.append(f"  Row {i+1}: trace_id has INVALID format: '{tid}'")
        continue

    # Check 3: duplicate detection (skip known test UUIDs)
    if tid in TEST_UUIDS:
        skipped_test_uuids += 1
        # Still record it but don't flag as error
        seen_traces[tid] = seen_traces.get(tid, i + 1)
    else:
        if tid in seen_traces:
            errors.append(
                f"  Row {i+1}: DUPLICATE trace_id '{tid[:8]}...' "
                f"(first seen at row {seen_traces[tid]})"
            )
        else:
            seen_traces[tid] = i + 1

    # Check 4: stage label correct
    if stage != "signal_ingest":
        errors.append(f"  Row {i+1}: Unexpected stage '{stage}' (expected 'signal_ingest')")

real_unique = len([t for t in seen_traces if t not in TEST_UUIDS])

# ── Results ───────────────────────────────────────────────────────────────────
log(f"  Real signal traces : {real_unique}")
log(f"  Test UUIDs (skipped from duplicate check) : {skipped_test_uuids}")

if errors:
    log(f"\n  [FAIL] {len(errors)} issue(s) found:")
    for e in errors:
        log(e)
    overall = False
else:
    log(f"\n  [PASS] All {len(entries)} trace entries validated successfully")
    log("  No missing trace_ids")
    log("  No invalid UUID4 formats")
    log("  No real duplicate trace_ids")
    log("  All entries correctly staged as 'signal_ingest'")
    log(f"  Known test UUID excluded from duplicate check: {list(TEST_UUIDS)[0]}")
    log("\n  TRACE CONTINUITY AT SIGNAL LAYER: CONFIRMED")
    overall = True

log(f"\n  Results saved: {OUT_FILE}")
log("=" * 65)

# ── Save ──────────────────────────────────────────────────────────────────────
txt_out = os.path.join(BASE_DIR, "validate_trace_log.txt")
with open(txt_out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "run_at":            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_entries":     len(entries),
        "real_signal_traces": real_unique,
        "test_uuids_skipped": skipped_test_uuids,
        "overall_pass":      overall,
        "errors":            errors
    }, f, indent=2)