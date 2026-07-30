"""
SVACS — operator_replay_engine.py
===================================
Phase 1: Operator Replay System

Given any trace_id, reconstructs the complete incident lifecycle
by reading all pipeline log files and assembling a single
structured replay object.

Usage:
    python operator_replay_engine.py --latest
    python operator_replay_engine.py --trace <trace_id>
    python operator_replay_engine.py --all
"""

import json
import os
import sys
import argparse
from datetime import datetime
from datetime import datetime, timezone

# BASE is the current directory (services/data_layer)
# ROOT goes two levels up to reach svacs-demo/
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..", "..")

# All log files across the entire pipeline
# Each one is a JSONL file — one JSON object per line
LOG_FILES = {
    "signal":         os.path.join(ROOT, "api/ingestion_server/trace_log.jsonl"),
    "ingestion":      os.path.join(ROOT, "api/ingestion_server/ingestion_log.jsonl"),
    "perception":     os.path.join(BASE, "perception_integration_log.jsonl"),
    "transformation": os.path.join(BASE, "transformation_log.jsonl"),
    "pipeline":       os.path.join(BASE, "full_pipeline_log.jsonl"),
    "bucket":         os.path.join(BASE, "bucket_verification_log.jsonl"),
}

# Where to save replay results
REPLAY_LOG = os.path.join(BASE, "replay_log.jsonl")


def load_jsonl(path: str) -> list:
    """
    Read a JSONL file and return a list of dicts.
    Each line in the file is one JSON object.
    Returns empty list if file doesn't exist.
    """
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def find_by_trace(records: list, trace_id: str) -> list:
    """
    Search a list of log records for any that contain the given trace_id.
    Checks three possible field names because different logs use different keys.
    """
    matches = []
    for r in records:
        if (r.get("trace_id") == trace_id or
            r.get("input_trace_id") == trace_id or
            r.get("output_trace_id") == trace_id):
            matches.append(r)
    return matches


def extract_replay_object(trace_id: str) -> dict:
    """
    Main function: builds the complete replay object for one trace_id.
    Reads all log files, finds matching records, assembles everything
    into one structured dict.
    """
    replay = {
        "trace_id":         trace_id,
        "replay_timestamp": datetime.now(timezone.utc).isoformat(),
        "stages":           {},   # data found at each stage
        "timeline":         [],   # chronological list of events
        "anomaly_summary":  {},   # what anomalies were detected
        "latency_ms":       {},   # how long each stage took
        "intelligence_chain": {}, # NICAI risk + validation result
        "continuity_proof": {},   # did trace_id stay the same throughout
        "gaps":             [],   # which stages had no data
    }

    # ── STAGE 1: Signal Ingest ────────────────────────────────────────────────
    # Read trace_log.jsonl — logged by mock_server.py when a chunk is accepted
    signal_records = find_by_trace(load_jsonl(LOG_FILES["signal"]), trace_id)
    if signal_records:
        r = signal_records[0]
        replay["stages"]["signal"] = {
            "trace_id":    r.get("trace_id"),
            "vessel_type": r.get("vessel_type"),
            "chunk_ts":    r.get("chunk_ts"),
            "server_ts":   r.get("server_ts"),
        }
        # Add to chronological timeline
        replay["timeline"].append({
            "stage":       "signal_ingest",
            "vessel_type": r.get("vessel_type"),
            "ts":          r.get("server_ts"),
        })
    else:
        replay["gaps"].append("signal")

    # ── STAGE 2: Full Pipeline ────────────────────────────────────────────────
    # Read full_pipeline_log.jsonl — logged by pipeline_connector.py
    # This is the richest log — contains perception, intelligence, state all in one
    pipeline_records = find_by_trace(load_jsonl(LOG_FILES["pipeline"]), trace_id)
    if pipeline_records:
        r = pipeline_records[0]

        # Extract perception_event from the pipeline log
        pe = r.get("perception_event") or {}
        if pe:
            replay["stages"]["perception"] = {
                "trace_id":         pe.get("trace_id"),
                "vessel_type":      pe.get("vessel_type"),
                "confidence_score": pe.get("confidence_score"),
                "dominant_freq_hz": pe.get("dominant_freq_hz"),
                "anomaly_flag":     pe.get("anomaly_flag"),
            }
            replay["timeline"].append({
                "stage":            "perception",
                "vessel_type":      pe.get("vessel_type"),
                "confidence":       pe.get("confidence_score"),
                "anomaly":          pe.get("anomaly_flag"),
                "dominant_freq_hz": pe.get("dominant_freq_hz"),
            })

        # Extract intelligence_event
        ie = r.get("intelligence_event") or {}
        if ie:
            replay["stages"]["intelligence"] = {
                "trace_id":          ie.get("trace_id"),
                "risk_level":        ie.get("risk_level"),
                "confidence":        ie.get("confidence"),
                "anomaly_flag":      ie.get("anomaly_flag"),
                "explanation":       ie.get("explanation"),
                "validation_status": ie.get("validation_status"),
            }
            # Store the intelligence chain separately for easy access
            replay["intelligence_chain"] = {
                "risk_level":        ie.get("risk_level"),
                "validation_status": ie.get("validation_status"),
                "explanation":       ie.get("explanation"),
            }
            replay["timeline"].append({
                "stage":             "intelligence",
                "risk_level":        ie.get("risk_level"),
                "validation_status": ie.get("validation_status"),
            })

        # Extract state_event
        se = r.get("state_event") or {}
        if se and "error" not in se:
            replay["stages"]["state"] = se
            replay["timeline"].append({
                "stage": "state",
                "data":  se,
            })

        # Latency and trace continuity
        replay["latency_ms"]["full_pipeline"] = r.get("latency_ms")
        replay["continuity_proof"] = r.get("trace_continuity") or {}
        replay["temporal_summary"] = r.get("temporal_summary") or {}

    else:
        replay["gaps"].append("pipeline")

    # ── STAGE 3: Bucket ───────────────────────────────────────────────────────
    bucket_records = find_by_trace(load_jsonl(LOG_FILES["bucket"]), trace_id)
    if bucket_records:
        replay["stages"]["bucket"] = bucket_records
        passed = [b for b in bucket_records if b.get("status") == "PASS"]
        replay["bucket_summary"] = {
            "total":  len(bucket_records),
            "passed": len(passed),
            "stages": [b.get("stage") for b in bucket_records],
        }
    else:
        replay["gaps"].append("bucket")

    # ── ANOMALY SUMMARY ───────────────────────────────────────────────────────
    pe = replay["stages"].get("perception", {})
    ie = replay["stages"].get("intelligence", {})
    replay["anomaly_summary"] = {
        "anomaly_flag":      pe.get("anomaly_flag"),
        "risk_level":        ie.get("risk_level"),
        "validation_status": ie.get("validation_status"),
        "dominant_freq_hz":  pe.get("dominant_freq_hz"),
        "confidence_score":  pe.get("confidence_score"),
    }

    # ── FINAL VERDICT ─────────────────────────────────────────────────────────
    # Tells the operator: is this trace fully reconstructable?
    stages_found = list(replay["stages"].keys())
    replay["verdict"] = {
        "trace_continuity": replay["continuity_proof"].get("all_match", False),
        "stages_found":     stages_found,
        "stages_missing":   replay["gaps"],
        "complete":         len(replay["gaps"]) == 0,
    }

    return replay


def print_replay(replay: dict):
    """Print a clean human-readable replay to the terminal."""
    print("\n" + "=" * 68)
    print(f"  OPERATOR REPLAY")
    print(f"  trace_id : {replay['trace_id']}")
    print(f"  replayed : {replay['replay_timestamp']}")
    print("=" * 68)

    print("\n  STAGES FOUND")
    print("  " + "-" * 50)
    for stage, data in replay["stages"].items():
        if isinstance(data, list):
            print(f"  [{stage.upper():<14}] {len(data)} artifact(s)")
        else:
            vtype = data.get("vessel_type", "N/A")
            tid_ok = data.get("trace_id") == replay["trace_id"]
            print(f"  [{stage.upper():<14}] vessel={vtype:<12} trace_ok={tid_ok}")

    print("\n  INTELLIGENCE CHAIN")
    print("  " + "-" * 50)
    ic = replay.get("intelligence_chain", {})
    print(f"  Risk Level    : {ic.get('risk_level', 'N/A')}")
    print(f"  Validation    : {ic.get('validation_status', 'N/A')}")
    print(f"  Explanation   : {ic.get('explanation', 'N/A')}")

    print("\n  ANOMALY SUMMARY")
    print("  " + "-" * 50)
    a = replay.get("anomaly_summary", {})
    print(f"  Anomaly Flag  : {a.get('anomaly_flag')}")
    print(f"  Dominant Freq : {a.get('dominant_freq_hz')} Hz")
    print(f"  Confidence    : {a.get('confidence_score')}")
    print(f"  Risk Level    : {a.get('risk_level')}")

    print("\n  LATENCY")
    print("  " + "-" * 50)
    for stage, ms in replay.get("latency_ms", {}).items():
        print(f"  {stage:<20}: {ms} ms")

    print("\n  VERDICT")
    print("  " + "-" * 50)
    v = replay.get("verdict", {})
    print(f"  Trace OK      : {v.get('trace_continuity')}")
    print(f"  Stages found  : {v.get('stages_found')}")
    print(f"  Missing       : {v.get('stages_missing')}")
    print(f"  Complete      : {v.get('complete')}")
    print("=" * 68 + "\n")


def get_latest_trace_id() -> str:
    """Get the most recent trace_id from full_pipeline_log.jsonl."""
    records = load_jsonl(LOG_FILES["pipeline"])
    for r in reversed(records):
        tid = r.get("trace_id")
        if tid:
            return tid
    # Fallback to signal log
    records = load_jsonl(LOG_FILES["signal"])
    for r in reversed(records):
        tid = r.get("trace_id")
        if tid:
            return tid
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SVACS Operator Replay Engine")
    parser.add_argument("--trace",  type=str,  help="Specific trace_id to replay")
    parser.add_argument("--latest", action="store_true", help="Replay most recent trace")
    parser.add_argument("--all",    action="store_true", help="Replay last 5 traces")
    args = parser.parse_args()

    if args.trace:
        # Replay a specific trace_id
        replay = extract_replay_object(args.trace)
        print_replay(replay)
        with open(REPLAY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(replay) + "\n")

    elif args.all:
        # Replay last 5 traces from pipeline log
        records = load_jsonl(LOG_FILES["pipeline"])
        seen = set()
        trace_ids = []
        for r in reversed(records):
            tid = r.get("trace_id")
            if tid and tid not in seen:
                trace_ids.append(tid)
                seen.add(tid)
            if len(trace_ids) == 5:
                break
        for tid in trace_ids:
            replay = extract_replay_object(tid)
            print_replay(replay)
            with open(REPLAY_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(replay) + "\n")

    else:
        # Default: replay latest trace
        tid = get_latest_trace_id()
        if not tid:
            print("[ERROR] No trace_ids found in logs. Run the pipeline first.")
            sys.exit(1)
        print(f"Using latest trace_id: {tid}")
        replay = extract_replay_object(tid)
        print_replay(replay)
        with open(REPLAY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(replay) + "\n")