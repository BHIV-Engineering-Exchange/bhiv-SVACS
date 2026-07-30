"""
Trace Validator
===============
Enforces trace_id continuity across the SVACS pipeline.

Rules:
  - trace_id must be present (not None)
  - trace_id must be non-empty after stripping whitespace
  - trace_id must remain identical across every stage
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional, Tuple

from schemas.state_event import IntelligenceEvent


def validate_trace(event: IntelligenceEvent) -> Tuple[bool, str]:
    """
    Validate that the intelligence event carries a valid trace_id.

    Returns:
        (True, "")          — trace_id is valid
        (False, reason_str) — trace_id is missing or empty
    """
    if event.trace_id is None:
        return False, "trace_id is None -- event rejected"

    if not event.trace_id.strip():
        return False, "trace_id is empty/whitespace -- event rejected"

    return True, ""


class TraceValidationError(ValueError):
    """Raised when a stage receives a missing or invalid trace_id."""


class TraceContinuityError(ValueError):
    """Raised when trace_id changes between pipeline stages."""


def ensure_valid_trace_id(trace_id: Optional[str], stage: str) -> str:
    """Return the original trace_id when valid, otherwise raise explicitly."""
    if trace_id is None:
        raise TraceValidationError(f"trace_id is None at {stage}")

    if not trace_id.strip():
        raise TraceValidationError(f"trace_id is empty/whitespace at {stage}")

    return trace_id


def ensure_trace_match(
    expected_trace_id: str,
    actual_trace_id: str,
    source_stage: str,
    target_stage: str,
) -> None:
    """Raise when trace_id changes between adjacent stages."""
    if expected_trace_id != actual_trace_id:
        raise TraceContinuityError(
            "trace_id mismatch between "
            f"{source_stage} and {target_stage}: "
            f"expected '{expected_trace_id}' but got '{actual_trace_id}'"
        )


def ensure_trace_chain(
    stage_events: Sequence[tuple[str, Mapping[str, Any]]],
) -> str:
    """Raise when any stage in a pipeline run diverges from the first trace_id."""
    if not stage_events:
        raise TraceValidationError("trace chain is empty")

    baseline_trace_id = ""
    baseline_stage = ""

    for index, (stage_name, payload) in enumerate(stage_events):
        current_trace_id = ensure_valid_trace_id(
            payload.get("trace_id"),
            stage=stage_name,
        )

        if index == 0:
            baseline_trace_id = current_trace_id
            baseline_stage = stage_name
            continue

        ensure_trace_match(
            expected_trace_id=baseline_trace_id,
            actual_trace_id=current_trace_id,
            source_stage=baseline_stage,
            target_stage=stage_name,
        )

    return baseline_trace_id
