"""
InsightFlow / Pravah Emitter
============================
Passive emission layer — NO logic, NO decisions.

Emits:
  - state
  - latency (ms)
  - trace_id

Output is consumed by InsightFlow → Dashboard.
"""

from __future__ import annotations

import logging
from typing import Optional

from schemas.state_event import StateEvent

logger = logging.getLogger("insightflow.emitter")


def emit_to_insightflow(
    state_event: StateEvent,
    latency_ms: float,
) -> dict:
    """
    Passively emit state telemetry to InsightFlow / Pravah.

    In production this would push to a message bus or HTTP endpoint.
    Currently logs the payload for downstream consumption.

    Returns the emitted payload dict for testability.
    """
    payload = {
        "trace_id": state_event.trace_id,
        "state": state_event.state.value,
        "latency_ms": round(latency_ms, 3),
        "timestamp": state_event.timestamp,
    }
    logger.info("InsightFlow emit: %s", payload)
    return payload
