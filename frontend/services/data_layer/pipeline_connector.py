"""
SVACS — pipeline_connector.py
================================
Connects the full pipeline:
  signal_chunk → perception_event → intelligence_event → state_event

Current status:
   Perception    — live (your perception_node.py)
   NICAI         — fill NICAI_ENDPOINT when Ankita shares URL
   State Engine  — fill STATE_ENDPOINT when Raj shares URL
   Bucket        — Siddhesh's endpoints confirmed (localhost:8000/bucket/...)

Usage:
    python pipeline_connector.py              # runs 5 test chunks
    python pipeline_connector.py --count 20  # runs 20 chunks (Phase 3)
"""


import json
import os
import sys
import time
import argparse
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'intelligence'))
from vessel_intelligence_engine import process_intelligence
from perception_node import process_signal
from hybrid_signal_builder import HybridSignalBuilder
from temporal_aggregator import TemporalAggregator
from bucket_verification import verify_bucket, verify_trace_bucket
from execution_observability import ObservabilityLogger


obs = ObservabilityLogger()


# ── Endpoints  ──────────────────────────────────
NICAI_ENDPOINT  = "https://dumping-jingle-daylight.ngrok-free.dev/nicai/classify"   # ← Ankita
STATE_ENDPOINT  = "http://127.0.0.1:8001/ingest/intelligence"     # ← Raj
BUCKET_BASE     = "https://bhiv-bucket-i1l6.onrender.com"       # ← Siddhesh
# ─────────────────────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(BASE_DIR, "full_pipeline_log.jsonl")



# Ankita's intelligence_event fields
INTELLIGENCE_FIELDS = [
    "trace_id", "vessel_type", "confidence",
    "risk_level", "anomaly_flag", "explanation", "validation_status"
]

VESSEL_TYPES = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]


def send_to_nicai(perception_event: dict) -> dict:
    """Send perception_event to Ankita's NICAI. Returns intelligence_event."""
    try:
        r = requests.post(NICAI_ENDPOINT, json=perception_event,
                         headers={"Content-Type": "application/json"}, timeout=15)
        if r.status_code == 200:
            full_response = r.json()

            # Extract intelligence_event from Ankita's response wrapper
            intel = full_response.get("intelligence_event", {})

            # Pull vessel_type, confidence, anomaly_flag from perception_event
            # block as intelligence_event doesn't include them directly
            if not intel.get("vessel_type"):
                intel["vessel_type"] = (
                    full_response.get("perception_event", {}).get("vessel_type")
                )
            if not intel.get("confidence"):
                intel["confidence"] = (
                    full_response.get("perception_event", {}).get("confidence_score")
                )
            if intel.get("anomaly_flag") is None:
                intel["anomaly_flag"] = (
                    full_response.get("perception_event", {}).get("anomaly_flag")
                )

            # Verify trace_id was not changed
            if intel.get("trace_id") != perception_event.get("trace_id"):
                print(f"  [ERROR] trace_id mismatch after NICAI!")

            return intel

        return {
            "error": True,
            "reason": f"NICAI HTTP {r.status_code}",
            "trace_id": perception_event.get("trace_id"),
            "validation_status": "FLAG",
        }
    except Exception as e:
        return {
            "error": True,
            "reason": str(e),
            "trace_id": perception_event.get("trace_id"),
            "validation_status": "FLAG",
        }


def send_to_state_engine(intelligence_event: dict) -> dict:
    try:
        r = requests.post(
            STATE_ENDPOINT,
            json=intelligence_event,
            headers={
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            timeout=10
        )
        if r.status_code == 200:
            state = r.json()
            if state.get("trace_id") != intelligence_event.get("trace_id"):
                print(f"  [ERROR] State Engine changed trace_id!")
            return state
        return {
            "error": True,
            "reason": f"State Engine HTTP {r.status_code}",
            "trace_id": intelligence_event.get("trace_id"),
        }
    except Exception as e:
        return {
            "error": True,
            "reason": str(e),
            "trace_id": intelligence_event.get("trace_id"),
        }


def verify_trace_continuity(signal_chunk, perception_event,
                             intelligence_event, state_event) -> dict:
    """Verify trace_id is identical across all 4 stages."""
    tid = signal_chunk["trace_id"]
    checks = {
        "signal":       signal_chunk.get("trace_id") == tid,
        "perception":   perception_event.get("trace_id") == tid,
        "intelligence": intelligence_event.get("trace_id") == tid,
        "state":        state_event.get("trace_id") == tid,
    }
    return {
        "trace_id":  tid,
        "checks":    checks,
        "all_match": all(checks.values()),
    }


def run_pipeline(signal_chunk: dict, aggregator: TemporalAggregator,
                 run_bucket: bool = True, bucket_start_hash: str = None) -> dict:
    """
    Full pipeline for one signal_chunk.
    Returns complete result dict.
    """
    t_start  = time.time()
    trace_id = signal_chunk["trace_id"]
    vtype    = signal_chunk.get("vessel_type")

    print(f"\n  [PIPELINE] trace={trace_id[:8]}...  vessel={vtype}")


 # Write signal entry to trace_log so replay engine can find it
    import time as _time
    signal_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "api", "ingestion_server", "trace_log.jsonl")
    with open(signal_log_path, "a", encoding="utf-8") as _f:
        _f.write(json.dumps({
            "trace_id":   trace_id,
            "vessel_type": vtype,
            "chunk_ts":   signal_chunk.get("timestamp"),
            "server_ts":  _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
            "stage":      "signal_ingest",
            "source":     "pipeline_connector"
        }) + "\n")


    # Stage 1: Perception
    perception_event = process_signal(signal_chunk)
    if "error" in perception_event:
        print(f"  [FAIL] Perception error: {perception_event['reason']}")
        return {"error": True, "stage": "perception",
                "trace_id": trace_id, "reason": perception_event["reason"]}

    print(f"    → perception:   vessel={perception_event.get('vessel_type')}  "
          f"conf={perception_event.get('confidence_score')}  "
          f"anomaly={perception_event.get('anomaly_flag')}")

    # Stage 2: Temporal aggregation
    temporal_summary = aggregator.update(perception_event)

    # Stage 3: NICAI
    intelligence_event = send_to_nicai(perception_event)
    nicai_ok = "error" not in intelligence_event
    print(f"    → intelligence: "
          f"{'risk=' + str(intelligence_event.get('risk_level')) if nicai_ok else 'NICAI not connected'}  "
          f"validation={intelligence_event.get('validation_status', 'N/A')}")

    # Stage 4: State Engine
    # If NICAI failed, use local intelligence engine
    if not nicai_ok:
        local_intel_input = {
            "trace_id":           trace_id,
            "source_type":        "acoustic",
            "vessel_class":       perception_event.get("vessel_type", "unknown"),
            "confidence_score":   perception_event.get("confidence_score", 0.0),
            "visual_features":    [],
            "dimensions_estimate": {},
            "ais_data":           {},
            "timestamp_utc":      perception_event.get("timestamp_utc"),
        }
        local_result = process_intelligence(local_intel_input)
        intelligence_event = {
            "trace_id":          trace_id,
            "vessel_type":       local_result.get("vessel_class", "unknown"),
            "risk_level":        local_result.get("risk_level", "MEDIUM"),
            "anomaly_flag":      perception_event.get("anomaly_flag", False),
            "confidence":        local_result.get("confidence_score", 0.0),
            "validation_status": local_result.get("validation_status", "FLAG"),
            "explanation":       local_result.get("explanation", ""),
        }
    state_event = send_to_state_engine(intelligence_event)
    state_ok = "error" not in state_event
    print(f"    → state:        {'OK' if state_ok else 'State Engine not connected'}")


    # Log to observability
    obs.log_pipeline_run(
        trace_id=trace_id,
        vessel_type=vtype,
        passed=(nicai_ok and state_ok),
        latency_ms=round((time.time() - t_start) * 1000, 2),
        nicai_allow=intelligence_event.get("validation_status") == "ALLOW",
        state_ok=state_ok,
        trace_continuity=True  # updated after continuity check below
    )

    # Log anomaly escalation if detected
    if perception_event.get("anomaly_flag"):
        obs.log_anomaly_escalation(
            trace_id=trace_id,
            vessel_type=perception_event.get("vessel_type", "unknown"),
            risk_level=intelligence_event.get("risk_level", "UNKNOWN"),
            reasons=perception_event.get("anomaly_reasons", [])
        )

    # Log server disconnections
    if not nicai_ok:
        obs.log_server_status("NICAI", "DISCONNECTED",
                              intelligence_event.get("reason", "unknown"))
    if not state_ok:
        obs.log_server_status("StateEngine", "DISCONNECTED",
                              state_event.get("reason", "unknown"))
        

    # Stage 5: Trace continuity
    continuity = verify_trace_continuity(
        signal_chunk, perception_event, intelligence_event, state_event
    )
    print(f"    → trace:        {'ALL MATCH ' if continuity['all_match'] else 'MISMATCH '}")

    # Stage 6: Bucket verification (chained)
    bucket_results = {}
    if run_bucket:
        current_hash = bucket_start_hash  # use hash passed in from previous chunk
        for stage_name, event in [
            ("perception",   {**perception_event,   "stage": "perception",   "pipeline": "SVACS"}),
            ("intelligence", {**intelligence_event, "stage": "intelligence", "pipeline": "SVACS"}),
            ("state",        {**state_event,        "stage": "state",        "pipeline": "SVACS"}),
        ]:
            if "error" not in event:
                bucket_result = verify_bucket(event, stage=stage_name, parent_hash=current_hash)
                bucket_results[stage_name] = bucket_result
                current_hash = bucket_result.get("next_hash")

    latency_ms = round((time.time() - t_start) * 1000, 3)

    result = {
        "trace_id":          trace_id,
        "input_vessel":      vtype,
        "perception_event":  perception_event,
        "intelligence_event": intelligence_event,
        "state_event":       state_event,
        "validation_status": intelligence_event.get("validation_status", "N/A"),
        "trace_continuity":  continuity,
        "temporal_summary":  temporal_summary,
        "bucket_results":    bucket_results,
        "latency_ms":        latency_ms,
        "timestamp":         time.time(),
    }

    # Log (without large sample arrays)
    log_entry = {k: v for k, v in result.items()}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    return result


def run_full_pipeline(count: int = 5, run_bucket: bool = True):
    """Run pipeline for `count` chunks across all 5 vessel types."""
    print("=" * 68)
    print("  SVACS — FULL PIPELINE EXECUTION")
    print(f"  Chunks: {count} | Bucket verification: {run_bucket}")
    print(f"  Run at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print("=" * 68)

    builder    = HybridSignalBuilder(sample_rate=4000, duration=1.0)
    aggregator = TemporalAggregator(window_size=5)

    results   = []
    passed    = 0
    failed    = 0
    latencies = []
    current_hash = None

    # Cycle through vessel types to ensure all 5 are covered
    for i in range(count):
        vtype = VESSEL_TYPES[i % len(VESSEL_TYPES)]
        chunk = builder.build(vtype)
        result = run_pipeline(chunk, aggregator, run_bucket=run_bucket,bucket_start_hash=current_hash)

        # Update hash for next chunk
        if run_bucket and result.get("bucket_results"):
            for stage_result in result["bucket_results"].values():
                if stage_result.get("next_hash"):
                    current_hash = stage_result["next_hash"]

        if "error" not in result:
            passed += 1
            latencies.append(result["latency_ms"])
        else:
            failed += 1

        results.append(result)
        time.sleep(0.05)

    # Summary
    print("\n" + "=" * 68)
    print("  PIPELINE SUMMARY")
    print("=" * 68)
    print(f"  Total chunks    : {count}")
    print(f"  Passed          : {passed}")
    print(f"  Failed          : {failed}")

    if latencies:
        avg_lat = round(sum(latencies) / len(latencies), 2)
        max_lat = round(max(latencies), 2)
        print(f"  Avg latency     : {avg_lat} ms")
        print(f"  Max latency     : {max_lat} ms")

    # Trace continuity summary
    trace_ok = sum(1 for r in results
                   if r.get("trace_continuity", {}).get("all_match"))
    print(f"  Trace continuity: {trace_ok}/{count}")

    # Validation status summary
    allow = sum(1 for r in results if r.get("validation_status") == "ALLOW")
    flag  = sum(1 for r in results if r.get("validation_status") == "FLAG")
    print(f"  NICAI ALLOW     : {allow}")
    print(f"  NICAI FLAG      : {flag}")

    # Bucket summary
    if run_bucket:
        bucket_pass = sum(
            1 for r in results
            if all(v.get("status") == "PASS"
                   for v in r.get("bucket_results", {}).values())
        )
        print(f"  Bucket verified : {bucket_pass}/{count}")

    # Temporal summaries
    print("\n  TEMPORAL AGGREGATION (final window state):")
    for vtype, s in aggregator.all_summaries().items():
        print(f"    {vtype:<16}: avg_conf={s['avg_confidence']}  "
              f"anomaly_rate={s['anomaly_rate']}  trend={s['anomaly_trend']}")

    print(f"\n  Log saved: {LOG_FILE}")
    print("=" * 68)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5,
                        help="Number of chunks to run (use 25 for Phase 3)")
    parser.add_argument("--no-bucket", action="store_true",
                        help="Skip bucket verification")
    args = parser.parse_args()

    run_full_pipeline(count=args.count, run_bucket=not args.no_bucket)