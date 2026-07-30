"""
SVACS — trace_reconstruction.py
=================================
Given a trace_id, reconstructs the full event lifecycle
across all pipeline stages from log files.

Usage:
    python trace_reconstruction.py <trace_id>
    python trace_reconstruction.py --latest
"""

import json
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..", "..")

LOG_FILES = {
    "1_signal_ingest":    os.path.join(ROOT, "api/ingestion_server/trace_log.jsonl"),
    "2_perception":       os.path.join(BASE, "perception_integration_log.jsonl"),
    "3_transformation":   os.path.join(BASE, "transformation_log.jsonl"),
    "4_full_pipeline":    os.path.join(BASE, "full_pipeline_log.jsonl"),
    "5_bucket":           os.path.join(BASE, "bucket_verification_log.jsonl"),
}


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        lines = []
        for line in f:
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return lines


def find_by_trace(records, trace_id):
    return [r for r in records if
            r.get("trace_id") == trace_id or
            r.get("input_trace_id") == trace_id or
            r.get("output_trace_id") == trace_id]


def reconstruct(trace_id):
    print("\n" + "=" * 68)
    print(f"  TRACE RECONSTRUCTION")
    print(f"  trace_id: {trace_id}")
    print("=" * 68)

    stages_found = []

    for stage, path in LOG_FILES.items():
        records = load_jsonl(path)
        matches = find_by_trace(records, trace_id)
        if matches:
            stages_found.append(stage)
            print(f"\n[{stage.upper()}]")
            for m in matches:
                clean = {k: v for k, v in m.items() if k != "samples"}
                print(json.dumps(clean, indent=2))
        else:
            print(f"\n[{stage.upper()}] — not found in {os.path.basename(path)}")

    # Continuity summary
    print("\n" + "=" * 68)
    print("  TRACE CONTINUITY SUMMARY")
    print("=" * 68)
    print(f"  trace_id found in {len(stages_found)}/{len(LOG_FILES)} stages\n")
    for stage in LOG_FILES:
        symbol = "FOUND" if stage in stages_found else "MISSING"
        print(f"  [{symbol}] {stage}")

    if len(stages_found) == len(LOG_FILES):
        print("\n  [PASS] Full trace continuity confirmed end-to-end")
    else:
        missing = [s for s in LOG_FILES if s not in stages_found]
        print(f"\n  [PARTIAL] Missing stages: {missing}")
        print("  (These stages may not be connected yet)")
    print("=" * 68 + "\n")


def get_latest_trace_id():
    records = load_jsonl(LOG_FILES["1_signal_ingest"])
    if not records:
        # Try full pipeline log as fallback
        records = load_jsonl(LOG_FILES["4_full_pipeline"])
    for r in reversed(records):
        tid = r.get("trace_id")
        if tid:
            return tid
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python trace_reconstruction.py <trace_id>")
        print("  python trace_reconstruction.py --latest")
        sys.exit(1)

    if sys.argv[1] == "--latest":
        tid = get_latest_trace_id()
        if not tid:
            print("[ERROR] No trace_ids found in any log file.")
            print("Run the pipeline first to generate logs.")
            sys.exit(1)
        print(f"Using latest trace_id: {tid}")
    else:
        tid = sys.argv[1]

    reconstruct(tid)