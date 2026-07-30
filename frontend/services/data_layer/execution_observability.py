"""
SVACS — execution_observability.py
=====================================
Phase 6: Execution Observability Layer

Single unified log for all pipeline events worth observing:
  - stage transitions
  - latency spikes
  - anomaly escalations
  - contract validation failures
  - dropped packets
  - bucket verification failures
  - server status changes

Output: execution_observability.jsonl
One JSON line per event. Append-only.

Usage:
    from execution_observability import ObservabilityLogger
    obs = ObservabilityLogger()
    obs.log_stage_transition("perception", "intelligence", trace_id, latency_ms=1250)
    obs.log_anomaly_escalation(trace_id, "unknown", "CRITICAL", ["multi-peak"])
"""

import json
import os
import time
from datetime import datetime, timezone

BASE    = os.path.dirname(os.path.abspath(__file__))
OBS_LOG = os.path.join(BASE, "execution_observability.jsonl")

# If a stage takes longer than this, flag it as a latency spike
# We set this high (5000ms) because ngrok adds overhead
LATENCY_SPIKE_THRESHOLD_MS = 5000


class ObservabilityLogger:
    """
    Unified observability logger for the SVACS pipeline.

    Every method writes one JSON line to execution_observability.jsonl.
    Each entry has:
      - event_type: what kind of event this is
      - obs_ts: Unix timestamp when this was logged
      - obs_ts_human: human-readable UTC timestamp
      - trace_id: which pipeline execution this belongs to (when applicable)
      - other fields specific to each event type
    """

    def __init__(self, log_path: str = None):
        # Allow custom log path for testing
        self.log_path = log_path or OBS_LOG

    def _write(self, entry: dict):
        """
        Internal method: add timestamps and write one line to the log.
        Called by all public methods.
        """
        # Add timestamps to every entry
        entry["obs_ts"]       = time.time()
        entry["obs_ts_human"] = datetime.now(timezone.utc).isoformat()
        # Append to log file — one JSON object per line
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_stage_transition(
        self,
        from_stage: str,
        to_stage: str,
        trace_id: str,
        latency_ms: float = None,
        status: str = "OK"
    ):
        """
        Log when the pipeline moves from one stage to the next.
        Also flags latency spikes automatically.

        Args:
            from_stage: e.g. "perception"
            to_stage:   e.g. "intelligence"
            trace_id:   the trace being processed
            latency_ms: how long this transition took
            status:     "OK" or "FAIL"
        """
        # Automatically detect latency spikes
        is_spike = (
            latency_ms is not None and
            latency_ms > LATENCY_SPIKE_THRESHOLD_MS
        )

        entry = {
            "event_type":    "STAGE_TRANSITION",
            "from_stage":    from_stage,
            "to_stage":      to_stage,
            "trace_id":      trace_id,
            "latency_ms":    latency_ms,
            "status":        status,
            "latency_spike": is_spike,
        }

        # Add a note explaining the spike if detected
        if is_spike:
            entry["spike_note"] = (
                f"Latency {latency_ms}ms exceeds threshold "
                f"{LATENCY_SPIKE_THRESHOLD_MS}ms. "
                f"Likely cause: ngrok network overhead."
            )

        self._write(entry)

    def log_anomaly_escalation(
        self,
        trace_id: str,
        vessel_type: str,
        risk_level: str,
        reasons: list = None
    ):
        """
        Log when an anomaly is detected and escalated.
        Called whenever anomaly_flag=True and risk is HIGH or CRITICAL.

        Args:
            trace_id:    the trace being processed
            vessel_type: what vessel type was classified
            risk_level:  LOW / MEDIUM / HIGH / CRITICAL
            reasons:     list of anomaly reason strings
        """
        self._write({
            "event_type":  "ANOMALY_ESCALATION",
            "trace_id":    trace_id,
            "vessel_type": vessel_type,
            "risk_level":  risk_level,
            "reasons":     reasons or [],
            "note":        f"Anomaly escalated to {risk_level} for {vessel_type} vessel.",
        })

    def log_contract_failure(
        self,
        trace_id: str,
        stage: str,
        reason: str,
        field: str = None
    ):
        """
        Log when a schema contract validation fails.
        e.g. missing required field, wrong type, invalid value.

        Args:
            trace_id: the trace being processed
            stage:    which stage failed validation
            reason:   human-readable failure reason
            field:    which specific field failed (optional)
        """
        self._write({
            "event_type": "CONTRACT_VALIDATION_FAILURE",
            "trace_id":   trace_id,
            "stage":      stage,
            "reason":     reason,
            "field":      field,
        })

    def log_dropped_packet(
        self,
        trace_id: str,
        stage: str,
        reason: str
    ):
        """
        Log when a signal chunk or event is dropped and not processed.
        e.g. server rejected it with HTTP 422, or connection timed out.

        Args:
            trace_id: the trace that was dropped
            stage:    where in the pipeline it was dropped
            reason:   why it was dropped
        """
        self._write({
            "event_type": "DROPPED_PACKET",
            "trace_id":   trace_id,
            "stage":      stage,
            "reason":     reason,
        })

    def log_bucket_failure(
        self,
        trace_id: str,
        stage: str,
        reason: str
    ):
        """
        Log when bucket write or read-back verification fails.

        Args:
            trace_id: the trace whose artifact failed
            stage:    perception / intelligence / state
            reason:   the error message
        """
        self._write({
            "event_type": "BUCKET_VERIFICATION_FAILURE",
            "trace_id":   trace_id,
            "stage":      stage,
            "reason":     reason,
        })

    def log_server_status(
        self,
        server: str,
        status: str,
        detail: str = None
    ):
        """
        Log when a teammate server goes up or down.
        e.g. NICAI ngrok dropped, State Engine disconnected.

        Args:
            server: "NICAI" / "StateEngine" / "Bucket" / "MockServer"
            status: "CONNECTED" / "DISCONNECTED" / "RECONNECTED"
            detail: optional extra info
        """
        self._write({
            "event_type": "SERVER_STATUS",
            "server":     server,
            "status":     status,
            "detail":     detail,
        })

    def log_pipeline_run(
        self,
        trace_id: str,
        vessel_type: str,
        passed: bool,
        latency_ms: float,
        nicai_allow: bool,
        state_ok: bool,
        trace_continuity: bool
    ):
        """
        Log a complete pipeline run summary for one chunk.
        Called at the end of each run_pipeline() execution.

        Args:
            trace_id:         the trace that was processed
            vessel_type:      input vessel type
            passed:           did the whole pipeline pass
            latency_ms:       total pipeline latency
            nicai_allow:      did NICAI return ALLOW
            state_ok:         did State Engine return OK
            trace_continuity: did trace_id stay the same throughout
        """
        self._write({
            "event_type":       "PIPELINE_RUN",
            "trace_id":         trace_id,
            "vessel_type":      vessel_type,
            "passed":           passed,
            "latency_ms":       latency_ms,
            "nicai_allow":      nicai_allow,
            "state_ok":         state_ok,
            "trace_continuity": trace_continuity,
        })

    def summarize(self) -> dict:
        """
        Read the observability log and return a summary of all events.
        Used for health checks and reporting.

        Returns:
            Dict with total count, counts per event type,
            and counts of spikes/anomalies/failures
        """
        if not os.path.exists(self.log_path):
            return {"total": 0, "events": {}, "message": "No observability log found yet."}

        # Read all records from the log
        records = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Count occurrences of each event type
        event_counts = {}
        for r in records:
            et = r.get("event_type", "UNKNOWN")
            event_counts[et] = event_counts.get(et, 0) + 1

        # Count specific concerns
        latency_spikes = [r for r in records if r.get("latency_spike") is True]
        anomalies      = [r for r in records
                          if r.get("event_type") == "ANOMALY_ESCALATION"]
        failures       = [r for r in records
                          if r.get("event_type") in (
                              "CONTRACT_VALIDATION_FAILURE",
                              "DROPPED_PACKET",
                              "BUCKET_VERIFICATION_FAILURE"
                          )]
        server_disconnects = [r for r in records
                               if r.get("event_type") == "SERVER_STATUS"
                               and r.get("status") == "DISCONNECTED"]

        return {
            "total_events":        len(records),
            "event_counts":        event_counts,
            "latency_spikes":      len(latency_spikes),
            "anomaly_escalations": len(anomalies),
            "failures":            len(failures),
            "server_disconnects":  len(server_disconnects),
            "log_path":            self.log_path,
        }


if __name__ == "__main__":
    print("=" * 65)
    print("  EXECUTION OBSERVABILITY — SELF TEST")
    print("=" * 65)

    # Create logger
    obs = ObservabilityLogger()

    # Simulate a series of pipeline events

    # 1. Normal stage transition
    obs.log_stage_transition(
        "perception", "intelligence",
        "trace-001", latency_ms=1250.5
    )
    print("[LOGGED] Stage transition: perception → intelligence (1250ms)")

    # 2. Latency spike — ngrok overhead
    obs.log_stage_transition(
        "intelligence", "state",
        "trace-001", latency_ms=6200.0
    )
    print("[LOGGED] Stage transition with LATENCY SPIKE: intelligence → state (6200ms)")

    # 3. Anomaly escalation
    obs.log_anomaly_escalation(
        "trace-002", "unknown", "CRITICAL",
        ["multi-peak", "unclear-band"]
    )
    print("[LOGGED] Anomaly escalation: unknown vessel → CRITICAL")

    # 4. Bucket failure
    obs.log_bucket_failure(
        "trace-003", "perception",
        "parent_hash stale — chain moved between runs"
    )
    print("[LOGGED] Bucket failure: stale parent_hash")

    # 5. Server disconnection
    obs.log_server_status("NICAI", "DISCONNECTED", "ngrok tunnel dropped")
    print("[LOGGED] Server status: NICAI DISCONNECTED")

    # 6. Server reconnection
    obs.log_server_status("NICAI", "RECONNECTED", "new ngrok URL active")
    print("[LOGGED] Server status: NICAI RECONNECTED")

    # 7. Full pipeline run
    obs.log_pipeline_run(
        "trace-004", "cargo",
        passed=True, latency_ms=1380.0,
        nicai_allow=True, state_ok=True,
        trace_continuity=True
    )
    print("[LOGGED] Pipeline run: cargo — PASS")

    # Show summary
    print("\n  SUMMARY:")
    summary = obs.summarize()
    import json as _json
    print(_json.dumps(summary, indent=2))
    print(f"\n  Log saved: {OBS_LOG}")
    print("=" * 65)