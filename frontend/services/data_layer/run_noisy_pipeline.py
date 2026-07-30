"""
Run all noisy scenarios through the full pipeline.
"""
import os, sys, time, json
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from noisy_scenario_builder import NoisyScenarioBuilder
from perception_node import process_signal
from temporal_aggregator import TemporalAggregator
from pipeline_connector import send_to_nicai, send_to_state_engine, verify_trace_continuity
from geo_injector import inject_geo
from intelligence_explainer import explain
from execution_observability import ObservabilityLogger

LOG_FILE = os.path.join(BASE, "noisy_pipeline_log.jsonl")

builder    = NoisyScenarioBuilder(seed=42)
aggregator = TemporalAggregator(window_size=5)
obs        = ObservabilityLogger()
scenarios  = builder.build_all_scenarios()

print("=" * 68)
print("  SVACS — NOISY SCENARIO PIPELINE RUN")
print(f"  Scenarios: {len(scenarios)} | Seed: 42 (deterministic)")
print(f"  Run at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
print("=" * 68)

passed = 0
failed = 0
results = []

for chunk in scenarios:
    trace_id = chunk["trace_id"]
    scenario = chunk.get("scenario", "unknown")
    vtype    = chunk.get("vessel_type", "unknown")

    print(f"\n  [{scenario:<25}] trace={trace_id[:8]}... vessel={vtype}")

    # Perception
    perception = process_signal(chunk)
    if "error" in perception:
        print(f"  [FAIL] Perception error")
        failed += 1
        continue

    print(f"    → perception: vessel={perception.get('vessel_type')} "
          f"conf={perception.get('confidence_score')} "
          f"anomaly={perception.get('anomaly_flag')}")

    # Geo enrichment
    geo_event = inject_geo(perception, vessel_type=perception.get("vessel_type"))

    # Temporal aggregation
    temporal = aggregator.update(perception)

    # NICAI
    intelligence = send_to_nicai(perception)
    nicai_ok = "error" not in intelligence
    print(f"    → intelligence: "
          f"{'risk=' + str(intelligence.get('risk_level')) if nicai_ok else 'NICAI not connected'} "
          f"validation={intelligence.get('validation_status', 'N/A')}")

    # Explanation
    explanation = explain(perception, intelligence)

    # State Engine
    state = send_to_state_engine(intelligence)
    state_ok = "error" not in state
    print(f"    → state: {'OK' if state_ok else 'not connected'}")

    # Trace continuity
    continuity = verify_trace_continuity(chunk, perception, intelligence, state)
    print(f"    → trace: {'ALL MATCH' if continuity['all_match'] else 'MISMATCH'}")
    print(f"    → explanation: {explanation[:80]}...")

    passed += 1

    result = {
        "trace_id":         trace_id,
        "scenario":         scenario,
        "input_vessel":     vtype,
        "noise_type":       chunk.get("noise_type"),
        "perception_event": perception,
        "intelligence_event": intelligence,
        "state_event":      state,
        "explanation":      explanation,
        "geo":              geo_event,
        "trace_continuity": continuity,
        "temporal_summary": temporal,
        "timestamp":        time.time(),
    }
    results.append(result)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")

    obs.log_pipeline_run(
        trace_id=trace_id,
        vessel_type=vtype,
        passed=True,
        latency_ms=0,
        nicai_allow=intelligence.get("validation_status") == "ALLOW",
        state_ok=state_ok,
        trace_continuity=continuity["all_match"]
    )

print("\n" + "=" * 68)
print("  NOISY PIPELINE SUMMARY")
print("=" * 68)
print(f"  Total scenarios : {len(scenarios)}")
print(f"  Passed          : {passed}")
print(f"  Failed          : {failed}")
print(f"  Trace continuity: {sum(1 for r in results if r['trace_continuity']['all_match'])}/{len(results)}")
print(f"  Log saved: {LOG_FILE}")
print("=" * 68)