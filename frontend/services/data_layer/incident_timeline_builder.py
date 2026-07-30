"""
SVACS — incident_timeline_builder.py
======================================
Phase 4: Operator Incident Timeline

Generates a chronological event timeline for UI rendering.
Output is structured JSON ready for Nikhil's dashboard.

Updated per Nikhil's requirements:
  - trace_id on every event
  - vessel_id on every event
  - timestamp on every event
  - latency_ms on every event
  - confidence_score on every event
  - anomaly_flag on every event
  - lat/lon geo coordinates on every event (via geo_injector)

Usage:
    python incident_timeline_builder.py --latest
    python incident_timeline_builder.py --trace <trace_id>
    python incident_timeline_builder.py --export
"""

import json
import os
import sys
import argparse
import time

BASE = os.path.dirname(os.path.abspath(__file__))

from operator_replay_engine import (
    extract_replay_object,
    load_jsonl,
    get_latest_trace_id,
)
from geo_injector import inject_geo

PIPELINE_LOG = os.path.join(BASE, "full_pipeline_log.jsonl")
TIMELINE_LOG = os.path.join(BASE, "incident_timelines.jsonl")


def make_vessel_id(vessel_type: str, trace_id: str) -> str:
    """
    Generate a deterministic vessel_id from vessel_type and trace_id.
    Format: VESSEL-{TYPE}-{first 8 chars of trace_id}
    e.g. VESSEL-CARGO-38ddb83b
    """
    vtype = (vessel_type or "UNKNOWN").upper()
    short_trace = (trace_id or "00000000")[:8]
    return f"VESSEL-{vtype}-{short_trace}"


def enrich_event(event: dict, vessel_type: str, trace_id: str,
                 confidence: float, anomaly: bool,
                 latency_ms: float, run_ts: float) -> dict:
    """
    Add all fields Nikhil requires to a timeline event.
    Injects geo coordinates using geo_injector.

    Args:
        event:       base event dict
        vessel_type: for geo zone selection and vessel_id
        trace_id:    the pipeline trace
        confidence:  classification confidence score
        anomaly:     anomaly flag
        latency_ms:  how long this stage took
        run_ts:      Unix timestamp of this pipeline run

    Returns:
        Enriched event dict with all required fields
    """
    # Generate geo coordinates for this vessel type
    geo_event = inject_geo(
        {"vessel_type": vessel_type, "confidence_score": confidence},
        vessel_type=vessel_type
    )

    return {
        **event,
        # Fields Nikhil specifically requested
        "trace_id":       trace_id,
        "vessel_id":      make_vessel_id(vessel_type, trace_id),
        "timestamp":      run_ts,
        "timestamp_human": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(run_ts)
        ),
        "latency_ms":     latency_ms,
        "confidence_score": confidence,
        "anomaly_flag":   anomaly,
        "lat":            geo_event.get("latitude"),
        "lon":            geo_event.get("longitude"),
        "heading_degrees": geo_event.get("heading_degrees"),
        "speed_knots":    geo_event.get("speed_knots"),
        "operational_zone": geo_event.get("operational_zone"),
        "geo_simulated":  True,
    }


def build_timeline(trace_id: str) -> dict:
    """
    Build a complete incident timeline from a trace_id.
    Every event includes all fields required by Nikhil's dashboard.

    Args:
        trace_id: the UUID4 trace to build a timeline for

    Returns:
        Timeline dict with ui_ready=True and enriched events list
    """
    replay   = extract_replay_object(trace_id)
    events   = []
    seq      = 1
    run_ts   = time.time()

    # Determine vessel type from whatever stage has it
    vessel_type = (
        replay["stages"].get("signal", {}).get("vessel_type") or
        replay["stages"].get("perception", {}).get("vessel_type") or
        replay["stages"].get("intelligence", {}).get("vessel_type") or
        "unknown"
    )

    # Overall confidence and anomaly from perception stage
    perception    = replay["stages"].get("perception", {})
    intelligence  = replay["stages"].get("intelligence", {})
    pipeline_lat  = replay.get("latency_ms", {}).get("full_pipeline", 0)

    base_confidence = (
        perception.get("confidence_score") or
        intelligence.get("confidence") or
        0.0
    )
    base_anomaly = (
        perception.get("anomaly_flag") or
        intelligence.get("anomaly_flag") or
        False
    )

    # ── Event 1: Signal Ingest ────────────────────────────────────────────────
    signal = replay["stages"].get("signal", {})
    if signal:
        base = {
            "seq":    seq,
            "stage":  "SIGNAL_INGEST",
            "status": "RECEIVED",
            "details": (
                f"Signal ingested from {vessel_type} vessel. "
                f"Chunk timestamp: {signal.get('chunk_ts', 'N/A')}."
            ),
        }
        events.append(enrich_event(
            base, vessel_type, trace_id,
            confidence=base_confidence,
            anomaly=base_anomaly,
            latency_ms=0,
            run_ts=run_ts,
        ))
        seq += 1

    # ── Event 2: Perception ───────────────────────────────────────────────────
    if perception:
        anomaly    = perception.get("anomaly_flag", False)
        confidence = perception.get("confidence_score", 0.0)
        freq       = perception.get("dominant_freq_hz", 0.0)
        status     = "ANOMALY_DETECTED" if anomaly else "CLASSIFIED"

        base = {
            "seq":           seq,
            "stage":         "PERCEPTION",
            "status":        status,
            "dominant_freq": freq,
            "details": (
                f"FFT: dominant frequency {freq} Hz. "
                f"Classified as {vessel_type.upper()} "
                f"with confidence {confidence}. "
                f"Anomaly: {'YES' if anomaly else 'NO'}."
            ),
        }
        events.append(enrich_event(
            base, vessel_type, trace_id,
            confidence=confidence,
            anomaly=anomaly,
            latency_ms=round(pipeline_lat * 0.1, 2),
            run_ts=run_ts + 0.1,
        ))
        seq += 1

    # ── Event 3: Intelligence ─────────────────────────────────────────────────
    if intelligence:
        risk       = intelligence.get("risk_level", "UNKNOWN")
        validation = intelligence.get("validation_status", "UNKNOWN")
        explanation = intelligence.get("explanation", "")
        escalated  = risk in ("HIGH", "CRITICAL")
        status     = "ESCALATED" if escalated else "ASSESSED"
        confidence = intelligence.get("confidence") or base_confidence
        anomaly    = intelligence.get("anomaly_flag") or base_anomaly

        base = {
            "seq":               seq,
            "stage":             "INTELLIGENCE",
            "status":            status,
            "risk_level":        risk,
            "validation_status": validation,
            "details": (
                f"NICAI: risk={risk}, validation={validation}. "
                f"{explanation}"
            ),
        }
        events.append(enrich_event(
            base, vessel_type, trace_id,
            confidence=confidence,
            anomaly=anomaly,
            latency_ms=round(pipeline_lat * 0.5, 2),
            run_ts=run_ts + 0.5,
        ))
        seq += 1

    # ── Event 4: State Engine ─────────────────────────────────────────────────
    state = replay["stages"].get("state", {})
    if state and isinstance(state, dict) and "error" not in state:
        base = {
            "seq":        seq,
            "stage":      "STATE_ENGINE",
            "status":     "STATE_UPDATED",
            "state_data": state,
            "details":    f"State Engine processed. Response: {json.dumps(state)[:100]}",
        }
        events.append(enrich_event(
            base, vessel_type, trace_id,
            confidence=base_confidence,
            anomaly=base_anomaly,
            latency_ms=round(pipeline_lat * 0.8, 2),
            run_ts=run_ts + 0.8,
        ))
        seq += 1

    # ── Event 5: Bucket ───────────────────────────────────────────────────────
    bucket = replay.get("bucket_summary", {})
    if bucket:
        passed = bucket.get("passed", 0)
        total  = bucket.get("total", 0)
        status = "STORED" if passed > 0 else "PENDING"

        base = {
            "seq":     seq,
            "stage":   "BUCKET",
            "status":  status,
            "details": (
                f"Bucket: {passed}/{total} artifacts stored. "
                f"Stages: {bucket.get('stages', [])}."
            ),
        }
        events.append(enrich_event(
            base, vessel_type, trace_id,
            confidence=base_confidence,
            anomaly=base_anomaly,
            latency_ms=round(pipeline_lat, 2),
            run_ts=run_ts + 1.0,
        ))
        seq += 1

    # ── Determine overall incident severity ───────────────────────────────────
    risk = intelligence.get("risk_level", "UNKNOWN")
    if risk == "CRITICAL":
        severity = "CRITICAL"
    elif risk == "HIGH" or (base_anomaly and risk == "MEDIUM"):
        severity = "HIGH"
    elif risk == "MEDIUM":
        severity = "MEDIUM"
    elif risk == "LOW":
        severity = "LOW"
    else:
        severity = "UNKNOWN"

    # ── Final timeline object ─────────────────────────────────────────────────
    timeline = {
        # Core identification
        "trace_id":          trace_id,
        "vessel_id":         make_vessel_id(vessel_type, trace_id),
        "generated_at":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),

        # Incident summary
        "vessel_type":       vessel_type,
        "incident_severity": severity,
        "anomaly_detected":  base_anomaly,
        "risk_level":        risk,
        "validation_status": intelligence.get("validation_status", "UNKNOWN"),
        "confidence_score":  base_confidence,

        # Geo coordinates (top level for map overlay)
        "geo": inject_geo(
            {"vessel_type": vessel_type, "confidence_score": base_confidence},
            vessel_type=vessel_type
        ),

        # Pipeline metadata
        "total_events":     len(events),
        "stages_complete":  replay["verdict"].get("stages_found", []),
        "stages_missing":   replay["verdict"].get("stages_missing", []),
        "trace_continuity": replay["verdict"].get("trace_continuity"),
        "latency_ms":       replay.get("latency_ms", {}),
        "temporal_summary": replay.get("temporal_summary", {}),

        # The ordered event list — ready for Nikhil's timeline renderer
        "events":           events,

        # Dashboard flags
        "ui_ready":         True,
        "schema_version":   "2.0",  # updated with Nikhil's required fields
    }

    return timeline


def export_all_timelines(count: int = 5) -> list:
    """Export timelines for the last N pipeline runs."""
    records   = load_jsonl(PIPELINE_LOG)
    seen      = set()
    trace_ids = []
    for r in reversed(records):
        tid = r.get("trace_id")
        if tid and tid not in seen:
            trace_ids.append(tid)
            seen.add(tid)
        if len(trace_ids) == count:
            break

    timelines = []
    for tid in trace_ids:
        tl = build_timeline(tid)
        timelines.append(tl)
        with open(TIMELINE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(tl) + "\n")

    return timelines


def print_timeline_summary(tl: dict):
    """Print a clean summary of a timeline to terminal."""
    print("\n" + "=" * 65)
    print(f"  INCIDENT TIMELINE (schema_version={tl.get('schema_version')})")
    print(f"  trace_id  : {tl['trace_id']}")
    print(f"  vessel_id : {tl['vessel_id']}")
    print(f"  vessel    : {tl['vessel_type']}")
    print(f"  severity  : {tl['incident_severity']}")
    print(f"  anomaly   : {tl['anomaly_detected']}")
    print(f"  risk      : {tl['risk_level']}")
    print(f"  confidence: {tl['confidence_score']}")
    print(f"  ui_ready  : {tl['ui_ready']}")
    geo = tl.get("geo", {})
    print(f"  geo       : lat={geo.get('latitude')}  lon={geo.get('longitude')}  "
          f"zone={geo.get('operational_zone')}")
    print("=" * 65)
    print("\n  EVENT SEQUENCE:")
    print("  " + "-" * 55)
    for event in tl["events"]:
        print(f"  [{event['seq']}] {event['stage']:<16} → {event['status']}")
        print(f"      trace_id    : {event.get('trace_id', 'N/A')[:16]}...")
        print(f"      vessel_id   : {event.get('vessel_id', 'N/A')}")
        print(f"      timestamp   : {event.get('timestamp_human', 'N/A')}")
        print(f"      latency_ms  : {event.get('latency_ms', 'N/A')}")
        print(f"      confidence  : {event.get('confidence_score', 'N/A')}")
        print(f"      anomaly     : {event.get('anomaly_flag', 'N/A')}")
        print(f"      lat/lon     : {event.get('lat', 'N/A')} / {event.get('lon', 'N/A')}")
        print(f"      details     : {str(event.get('details', ''))[:70]}...")
        print()
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace",  type=str,  help="Specific trace_id")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--export", action="store_true",
                        help="Export last 5 timelines for Nikhil")
    args = parser.parse_args()

    if args.export:
        print("Exporting last 5 timelines for Nikhil's dashboard...")
        timelines = export_all_timelines(5)
        print(f"Exported {len(timelines)} timelines → {TIMELINE_LOG}")
        for tl in timelines:
            print(f"  trace={tl['trace_id'][:8]}...  "
                  f"vessel_id={tl['vessel_id']}  "
                  f"severity={tl['incident_severity']}  "
                  f"events={tl['total_events']}")

    elif args.trace:
        tl = build_timeline(args.trace)
        print_timeline_summary(tl)
        with open(TIMELINE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(tl) + "\n")
        print(f"[SAVED] {TIMELINE_LOG}")

    else:
        tid = get_latest_trace_id()
        if not tid:
            print("[ERROR] No trace_ids found. Run the pipeline first.")
            sys.exit(1)
        tl = build_timeline(tid)
        print_timeline_summary(tl)
        with open(TIMELINE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(tl) + "\n")
        print(f"[SAVED] {TIMELINE_LOG}")