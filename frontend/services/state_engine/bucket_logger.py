"""
Bucket Logger
=============
Mandatory logging layer — every event (incoming, outgoing, trace errors) is
persisted to a JSONL file for full auditability.

Each log entry includes:
  trace_id | input | output | state | timestamp
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from schemas.state_event import BucketLogEntry


def _entry_to_json(entry: BucketLogEntry) -> str:
    dump_json = getattr(entry, "model_dump_json", None)
    if callable(dump_json):
        return dump_json()
    return entry.json()


class BucketLogger:
    """Append-only JSONL logger writing to a configurable path."""

    def __init__(self, log_path: str = "logs/bucket.jsonl") -> None:
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_incoming(
        self,
        trace_id: Optional[str],
        event_dict: Dict[str, Any],
    ) -> BucketLogEntry:
        """Log a raw incoming intelligence_event."""
        entry = BucketLogEntry(
            log_type="incoming",
            trace_id=trace_id,
            input=event_dict,
            output=None,
            error=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._write(entry)
        return entry

    def log_outgoing(
        self,
        trace_id: str,
        input_dict: Dict[str, Any],
        output_dict: Dict[str, Any],
    ) -> BucketLogEntry:
        """Log a successful state_event emission."""
        entry = BucketLogEntry(
            log_type="outgoing",
            trace_id=trace_id,
            input=input_dict,
            output=output_dict,
            error=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._write(entry)
        return entry

    def log_trace_error(
        self,
        trace_id: Optional[str],
        event_dict: Dict[str, Any],
        error_msg: str,
    ) -> BucketLogEntry:
        """Log a trace validation failure."""
        entry = BucketLogEntry(
            log_type="trace_error",
            trace_id=trace_id,
            input=event_dict,
            output=None,
            error=error_msg,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._write(entry)
        return entry

    def log_state_stage(
        self,
        trace_id: str,
        state: str,
    ) -> BucketLogEntry:
        """Log the explicit state-engine stage output required for trace proof."""
        entry = BucketLogEntry(
            log_type="state_stage",
            trace_id=trace_id,
            stage="state_engine",
            state=state,
            input=None,
            output=None,
            error=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._write(entry)
        return entry

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _write(self, entry: BucketLogEntry) -> None:
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(_entry_to_json(entry) + "\n")
