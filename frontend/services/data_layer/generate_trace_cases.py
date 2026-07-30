"""
generate_trace_proof.py
========================
Generates 5 signal + perception cases (one per vessel type)
for end-to-end trace proof.

Output: 5_trace_cases.json

Run from: svacs-demo/services/data_layer/
  python generate_trace_cases.py
"""

import sys
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from hybrid_signal_builder import HybridSignalBuilder
from perception_node import process_signal

builder = HybridSignalBuilder(seed=99)
vessel_types = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]
output = []

print("=" * 68)
print("  SVACS — TRACE CASES GENERATOR")
print("  Generating 1 case per vessel type")
print("=" * 68)

for vtype in vessel_types:
    chunk = builder.build(vtype)
    perception_event = process_signal(chunk)

    trace_match = (chunk["trace_id"] == perception_event["trace_id"])

    case = {
        "vessel_type":  vtype,
        "trace_id":     chunk["trace_id"],
        "signal_event": {
            "trace_id":       chunk["trace_id"],
            "vessel_type":    chunk["vessel_type"],
            "timestamp":      chunk["timestamp"],
            "sample_rate":    chunk["sample_rate"],
            "snr_db":         chunk["snr_db"],
            "noise_floor_db": chunk["noise_floor_db"],
            "hybrid":         chunk["hybrid"],
            "n_samples":      len(chunk["samples"]),
        },
        "perception_event": perception_event,
        "trace_match": trace_match,
    }

    output.append(case)

    print(
        f"  {vtype:<16} | trace={chunk['trace_id'][:8]}... | "
        f"vessel={perception_event['vessel_type']:<12} | "
        f"conf={perception_event['confidence_score']} | "
        f"anomaly={perception_event['anomaly_flag']} | "
        f"trace_match={trace_match}"
    )

# Save
out_path = os.path.join(BASE_DIR, "5_trace_cases.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print()
print(f"  Saved: {out_path}")
print("=" * 68)
