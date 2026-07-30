"""
SVACS — temporal_aggregator.py
================================
Rolling window aggregator for perception_events.
Window size: last 3-5 events per vessel type.
Computes: average confidence, anomaly trend.
No ML. No probabilistic logic. Pure deterministic arithmetic.

Usage:
    from temporal_aggregator import TemporalAggregator
    agg = TemporalAggregator(window_size=5)
    summary = agg.update(perception_event)
"""

import json
import os
from collections import deque, defaultdict


class TemporalAggregator:
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self._windows = defaultdict(lambda: deque(maxlen=window_size))

    def update(self, perception_event: dict) -> dict:
        """Add perception_event to window. Returns current summary."""
        vessel = perception_event.get("vessel_type", "unknown")
        self._windows[vessel].append(perception_event)
        return self.summarize(vessel)

    def summarize(self, vessel_type: str) -> dict:
        """Deterministic summary over current window for a vessel type."""
        window = list(self._windows[vessel_type])
        if not window:
            return {"vessel_type": vessel_type, "window_size": 0}

        confidences   = [e.get("confidence_score", 0.0) for e in window]
        anomaly_flags = [bool(e.get("anomaly_flag", False)) for e in window]
        anomaly_count = sum(anomaly_flags)

        # Anomaly trend: compare first half vs second half of window
        mid = max(len(window) // 2, 1)
        first_half  = sum(1 for f in anomaly_flags[:mid] if f)
        second_half = sum(1 for f in anomaly_flags[mid:] if f)

        if second_half > first_half:
            anomaly_trend = "increasing"
        elif second_half < first_half:
            anomaly_trend = "decreasing"
        else:
            anomaly_trend = "stable"

        return {
            "vessel_type":    vessel_type,
            "window_size":    len(window),
            "avg_confidence": round(sum(confidences) / len(confidences), 4),
            "min_confidence": round(min(confidences), 4),
            "max_confidence": round(max(confidences), 4),
            "anomaly_count":  anomaly_count,
            "anomaly_rate":   round(anomaly_count / len(window), 4),
            "anomaly_trend":  anomaly_trend,
            "last_trace_id":  window[-1].get("trace_id"),
        }

    def all_summaries(self) -> dict:
        """Return temporal summary for all vessel types seen so far."""
        return {vtype: self.summarize(vtype) for vtype in self._windows}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from hybrid_signal_builder import HybridSignalBuilder
    from perception_node import process_signal

    print("=" * 65)
    print("  TEMPORAL AGGREGATOR — SELF TEST")
    print("  Window size: 5 | Vessel sequence: mixed")
    print("=" * 65)

    builder  = HybridSignalBuilder(seed=42)
    agg      = TemporalAggregator(window_size=5)

    sequence = [
        "cargo", "cargo", "cargo", "anomaly", "anomaly",
        "submarine", "cargo", "anomaly", "cargo", "submarine"
    ]

    for vtype in sequence:
        chunk   = builder.build(vtype)
        event   = process_signal(chunk)
        summary = agg.update(event)
        print(
            f"  [{vtype:<16}] → predicted={event.get('vessel_type'):<12} "
            f"avg_conf={summary['avg_confidence']}  "
            f"anomaly_rate={summary['anomaly_rate']}  "
            f"trend={summary['anomaly_trend']}"
        )

    print("\n  FINAL WINDOW SUMMARIES (all vessel types):")
    print("  " + "-" * 62)
    for vtype, s in agg.all_summaries().items():
        print(f"  {vtype:<16}: avg_conf={s['avg_confidence']}  "
              f"anomaly_rate={s['anomaly_rate']}  "
              f"trend={s['anomaly_trend']}  "
              f"window={s['window_size']}")
    print("=" * 65)