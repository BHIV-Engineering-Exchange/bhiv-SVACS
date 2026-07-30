"""
State Engine
============
Core deterministic state mapping layer.

Responsibility:
  1. Validate trace_id
  2. Convert intelligence risk into system state
  3. Preserve trace continuity into state_event
  4. Log audit records for UI and Mitra

Determinism guarantee:
  The same intelligence_event always maps to the same state.
  No randomness. No extra thresholds. No new decision system.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from bucket_logger import BucketLogger
from emitter import emit_to_insightflow
from schemas.state_event import IntelligenceEvent, RiskLevel, StateEvent, SystemState
from trace_validator import (
    TraceContinuityError,
    TraceValidationError,
    ensure_trace_match,
    ensure_valid_trace_id,
)


RISK_STATE_MAP = {
    RiskLevel.LOW: SystemState.NORMAL,
    RiskLevel.MEDIUM: SystemState.WARNING,
    RiskLevel.HIGH: SystemState.ALERT,
    RiskLevel.CRITICAL: SystemState.CRITICAL,
}

SHORT_LABEL_MAP = {
    SystemState.NORMAL: "Safe",
    SystemState.WARNING: "Watch",
    SystemState.ALERT: "Concern",
    SystemState.CRITICAL: "Threat",
}


def _model_to_dict(model: object) -> dict:
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    return model.dict()


class StateEngine:
    """Deterministic state assignment engine with trace enforcement."""

    def __init__(self, bucket_log_path: str = "logs/bucket.jsonl") -> None:
        self.bucket = BucketLogger(log_path=bucket_log_path)

    @staticmethod
    def map_state(risk_level: RiskLevel, anomaly_flag: bool) -> SystemState:
        """Map upstream risk to a UI-safe system state with anomaly override."""
        if anomaly_flag:
            return SystemState.CRITICAL

        return RISK_STATE_MAP[risk_level]

    def process(self, event: IntelligenceEvent) -> StateEvent:
        """Process a single intelligence_event into a stable state_event."""
        start = time.monotonic()
        event_dict = _model_to_dict(event)

        try:
            trace_id = ensure_valid_trace_id(
                event.trace_id,
                stage="state_engine.input",
            )
        except TraceValidationError as exc:
            self.bucket.log_trace_error(
                trace_id=event.trace_id,
                event_dict=event_dict,
                error_msg=str(exc),
            )
            raise

        self.bucket.log_incoming(
            trace_id=trace_id,
            event_dict=event_dict,
        )

        state = self.map_state(
            risk_level=event.risk_level,
            anomaly_flag=event.anomaly_flag,
        )
        state_event = StateEvent(
            trace_id=trace_id,
            vessel_type=event.vessel_type,
            risk_level=event.risk_level,
            state=state,
            anomaly_flag=event.anomaly_flag,
            timestamp=datetime.now(timezone.utc).isoformat(),
            short_label=SHORT_LABEL_MAP[state],
        )

        try:
            ensure_trace_match(
                expected_trace_id=trace_id,
                actual_trace_id=state_event.trace_id,
                source_stage="intelligence_event",
                target_stage="state_event",
            )
        except TraceContinuityError as exc:
            self.bucket.log_trace_error(
                trace_id=trace_id,
                event_dict={
                    "input": event_dict,
                    "output": _model_to_dict(state_event),
                },
                error_msg=str(exc),
            )
            raise

        state_dict = _model_to_dict(state_event)
        self.bucket.log_outgoing(
            trace_id=state_event.trace_id,
            input_dict=event_dict,
            output_dict=state_dict,
        )
        self.bucket.log_state_stage(
            trace_id=state_event.trace_id,
            state=state_event.state.value,
        )

        latency_ms = (time.monotonic() - start) * 1000
        emit_to_insightflow(state_event, latency_ms)

        return state_event
