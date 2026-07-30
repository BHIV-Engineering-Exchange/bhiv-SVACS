"""
SVACS Signal Layer -- streaming_simulator.py
============================================
Simulates real-time acoustic signal streaming to the SVACS pipeline.
20-50ms delay between chunks, non-blocking loop.
Every emitted chunk includes trace_id for end-to-end traceability.

Usage:
  python streaming_simulator.py --vessel cargo --duration 10
  python streaming_simulator.py --scenario scenarios/scenario_1_cargo.json
  python streaming_simulator.py --demo
  python streaming_simulator.py --vessel speedboat --endpoint http://localhost:8000/ingest/signal
"""

import time
import json
import argparse
import os
import random
from hybrid_signal_builder import HybridSignalBuilder


class StreamTransport:
    def __init__(self, endpoint=None, verbose=True):
        self.endpoint = endpoint
        self.verbose = verbose
        self._chunk_count = 0

    def send(self, chunk):
        self._chunk_count += 1
        if self.endpoint:
            self._send_http(chunk)
        else:
            self._send_print(chunk)

    def _send_print(self, chunk):
        if self.verbose:
            ts       = chunk.get("timestamp", 0)
            vtype    = chunk.get("vessel_type", "?")
            n        = len(chunk.get("samples", []))
            conf     = chunk.get("metadata", {}).get("confidence_expected", "?")
            tag      = chunk.get("metadata", {}).get("scenario_tag", "")
            trace_id = chunk.get("trace_id", "NO-TRACE")[:8]
            anomaly  = chunk.get("expected_label", {}).get("anomaly_flag", False)
            print(
                f"[STREAM #{self._chunk_count:04d}] "
                f"trace={trace_id}...  "
                f"ts={ts:.4f}  "
                f"vessel={vtype:<16}  "
                f"n={n}  conf={conf:<12}  "
                f"anomaly={anomaly}  tag={tag}"
            )

    def _send_http(self, chunk):
        try:
            import urllib.request
            payload = json.dumps(chunk).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint, data=payload,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if self.verbose:
                    trace_id = chunk.get("trace_id", "NO-TRACE")[:8]
                    print(f"[STREAM #{self._chunk_count:04d}] trace={trace_id}...  -> HTTP {resp.status} | vessel={chunk.get('vessel_type')}")
        except Exception as e:
            if self.verbose:
                print(f"[STREAM #{self._chunk_count:04d}] -> HTTP FAIL: {e}")


def stream_live(vessel_type, duration_seconds=10.0, delay_ms_min=20,
                delay_ms_max=50, endpoint=None, verbose=True):
    builder = HybridSignalBuilder(sample_rate=4000, duration=1.0)
    transport = StreamTransport(endpoint=endpoint, verbose=verbose)
    vessel_types = ["cargo", "ferry", "cruise", "roro", "passenger", "speedboat", "submarine", "low_confidence", "anomaly"]
    type_probs   = [0.15,    0.10,    0.10,     0.10,   0.10,        0.15,        0.10,        0.10,             0.10]
    use_rotation = (vessel_type == "all")
    start = time.time()
    chunk_idx = 0

    print(f"\n{'='*60}")
    print(f"SVACS LIVE STREAM STARTED")
    print(f"  Vessel   : {vessel_type}")
    print(f"  Duration : {duration_seconds}s")
    print(f"  Delay    : {delay_ms_min}-{delay_ms_max} ms")
    print(f"  Endpoint : {endpoint or 'PRINT MODE'}")
    print(f"{'='*60}\n")

    while (time.time() - start) < duration_seconds:
        if use_rotation:
            vt = np.random.choice(vessel_types, p=type_probs)
        else:
            vt = vessel_type
        try:
            chunk = builder.build(vt)
            transport.send(chunk)
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(random.uniform(delay_ms_min / 1000.0, delay_ms_max / 1000.0))
        chunk_idx += 1

    elapsed = time.time() - start
    print(f"\n[STREAM ENDED] {transport._chunk_count} chunks in {elapsed:.2f}s")


def stream_from_scenario(scenario_path, delay_ms_min=20, delay_ms_max=50,
                         endpoint=None, verbose=True, repeat=5):
    if not os.path.exists(scenario_path):
        print(f"[ERROR] File not found: {scenario_path}")
        return
    with open(scenario_path, "r") as f:
        scenario = json.load(f)

    chunk  = scenario.get("signal", {})
    labels = scenario.get("labels", {})
    name   = scenario.get("scenario_name", "unknown")
    transport = StreamTransport(endpoint=endpoint, verbose=verbose)

    print(f"\n{'='*60}")
    print(f"SVACS SCENARIO REPLAY: {name}")
    print(f"  Vessel Type    : {labels.get('vessel_type', '?')}")
    print(f"  Confidence     : {labels.get('expected_confidence', '?')}")
    print(f"  Anomaly Flag   : {labels.get('anomaly_flag', False)}")
    print(f"  Original Trace : {chunk.get('trace_id', 'N/A')}")
    print(f"  Repeat         : {repeat}x")
    print(f"{'='*60}\n")

    import uuid
    for i in range(repeat):
        # Each replay emission gets a fresh trace_id to track uniquely
        chunk["timestamp"] = time.time()
        chunk["trace_id"]  = str(uuid.uuid4())
        transport.send(chunk)
        time.sleep(random.uniform(delay_ms_min / 1000.0, delay_ms_max / 1000.0))

    print(f"\n[REPLAY DONE] {repeat} chunks sent for: {name}")


def stream_all_scenarios(scenarios_dir="scenarios", delay_ms_min=20, delay_ms_max=50,
                         endpoint=None, verbose=True, repeat_each=3):
    index_path = os.path.join(scenarios_dir, "index.json")
    if not os.path.exists(index_path):
        print(f"[ERROR] index.json not found. Run: python scenario_builder.py first.")
        return
    with open(index_path, "r") as f:
        index = json.load(f)

    print(f"\n{'='*60}")
    print(f"SVACS FULL DEMO SUITE -- {index['total']} scenarios")
    print(f"{'='*60}")

    for entry in index["scenarios"]:
        path = os.path.join(scenarios_dir, entry["file"])
        print(f"\n--- Scenario {entry['id']}: {entry['name']} ---")
        stream_from_scenario(path, delay_ms_min, delay_ms_max, endpoint, verbose, repeat_each)
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print("FULL DEMO SUITE COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SVACS Real-Time Signal Streaming Simulator")
    parser.add_argument("--vessel", type=str, default="cargo",
        choices=["cargo", "ferry", "cruise", "roro", "passenger", "speedboat", "submarine", "low_confidence", "anomaly", "all"])
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--scenario", type=str, default=None)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--endpoint", type=str, default=None)
    parser.add_argument("--delay-min", type=int, default=20)
    parser.add_argument("--delay-max", type=int, default=50)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    verbose = not args.quiet

    if args.demo:
        stream_all_scenarios(delay_ms_min=args.delay_min, delay_ms_max=args.delay_max,
                             endpoint=args.endpoint, verbose=verbose)
    elif args.scenario:
        stream_from_scenario(args.scenario, args.delay_min, args.delay_max,
                             args.endpoint, verbose)
    else:
        stream_live(args.vessel, args.duration, args.delay_min, args.delay_max,
                    args.endpoint, verbose)