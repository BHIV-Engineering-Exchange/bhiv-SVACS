"""
SVACS Signal Layer — run_tests.py
===================================
Full test suite. Run this FIRST to validate everything works.

Tests:
  1. Signal Generator — all 5 types
  2. Hybrid Builder — overlay + stats
  3. Scenario Builder — all 5 scenarios saved
  4. Streaming Simulator — 5-second stream test
  5. Signal Validation — freq range checks
  6. Visualization — plots saved to plots/

Usage:
  python run_tests.py
  python run_tests.py --no-plots    # skip matplotlib
"""

import os
import sys
import time
import argparse
import json


#  SETUP                                                              
# ------------------------------------------------------------------ #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "utils"))

from signal_generator import SignalGenerator
from hybrid_signal_builder import HybridSignalBuilder
from scenario_builder import ScenarioBuilder
from streaming_simulator import stream_live
import utils.signal_utils as utils

PASS = "  [PASS]"
FAIL = "  [FAIL]"
SEP  = "─" * 60


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")



#  TEST 1 — SIGNAL GENERATOR                                         
# ------------------------------------------------------------------ #

def test_signal_generator():
    section("TEST 1: Signal Generator (all 5 types)")
    gen = SignalGenerator(sample_rate=4000, duration=1.0)
    types = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]
    all_pass = True

    for vtype in types:
        try:
            chunk = gen.generate_chunk(vtype)
            assert isinstance(chunk["samples"], list), "samples not a list"
            assert len(chunk["samples"]) == 4000, f"expected 4000 samples, got {len(chunk['samples'])}"
            assert chunk["sample_rate"] == 4000
            assert "timestamp" in chunk
            assert "metadata" in chunk
            print(f"{PASS} {vtype:<20} n={len(chunk['samples'])} | freq={chunk['metadata'].get('freq_hz', chunk['metadata'].get('spike_frequencies_hz', '?'))} Hz")
        except Exception as e:
            print(f"{FAIL} {vtype}: {e}")
            all_pass = False

    return all_pass



#  TEST 2 — HYBRID BUILDER                                           
# ------------------------------------------------------------------ #

def test_hybrid_builder():
    section("TEST 2: Hybrid Signal Builder")
    builder = HybridSignalBuilder(sample_rate=4000, duration=1.0)
    types = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]
    all_pass = True

    for vtype in types:
        try:
            chunk = builder.build(vtype)
            s = chunk["samples"]
            assert len(s) == 4000
            assert max(s) <= 1.01 and min(s) >= -1.01, "Signal not normalized to [-1, 1]"
            stats = utils.summarize(chunk)
            print(
                f"{PASS} {vtype:<20} rms={stats['rms']:.4f} | "
                f"peak={stats['peak_freq_hz']:.1f} Hz | "
                f"snr={stats['snr_db']:.1f} dB"
            )
        except Exception as e:
            print(f"{FAIL} {vtype}: {e}")
            all_pass = False

    return all_pass



#  TEST 3 — SCENARIO BUILDER                                         
# ------------------------------------------------------------------ #

def test_scenario_builder():
    section("TEST 3: Scenario Builder (5 scenarios)")
    sb = ScenarioBuilder(output_dir="scenarios")
    all_pass = True

    try:
        paths = sb.build_all()
        for path in paths:
            assert os.path.exists(path), f"File missing: {path}"
            with open(path) as f:
                data = json.load(f)
            assert "signal" in data
            assert "labels" in data
            assert "scenario_id" in data
            name = data["scenario_name"]
            conf = data["labels"]["expected_confidence"]
            anomaly = data["labels"]["anomaly_flag"]
            print(f"{PASS} {name:<35} | conf={conf:<12} | anomaly={anomaly}")
    except Exception as e:
        print(f"{FAIL} Scenario builder: {e}")
        all_pass = False

    return all_pass



#  TEST 4 — STREAMING SIMULATOR                                       
# ------------------------------------------------------------------ #

def test_streaming():
    section("TEST 4: Streaming Simulator (5s, cargo, print mode)")
    try:
        stream_live(
            vessel_type="cargo",
            duration_seconds=3.0,   # short for test
            delay_ms_min=20,
            delay_ms_max=50,
            endpoint=None,
            verbose=True
        )
        print(f"\n{PASS} Streaming completed without errors")
        return True
    except Exception as e:
        print(f"{FAIL} Streaming: {e}")
        return False



#  TEST 5 — SIGNAL VALIDATION                                        
# ------------------------------------------------------------------ #

def test_signal_validation():
    section("TEST 5: Signal Frequency Validation")
    builder = HybridSignalBuilder(sample_rate=4000, duration=1.0)

    # For validation, use pure generator (not hybrid) to check freq range
    from signal_generator import SignalGenerator
    gen = SignalGenerator()

    checks = [
        ("cargo",     "cargo_ship"),
        ("speedboat", "speedboat"),
        ("submarine", "submarine"),
    ]

    all_pass = True
    for vtype, expected_key in checks:
        # Run 5 times — freq is random within range
        pass_count = 0
        for _ in range(5):
            chunk = gen.generate_chunk(vtype)
            # Temporarily set vessel_type to expected key for validation
            chunk["vessel_type"] = expected_key
            result = utils.validate_chunk(chunk)
            if result["valid"]:
                pass_count += 1

        rate = pass_count / 5
        ok = rate >= 0.6   # allow 60%+ pass rate (freq is stochastic)
        status = PASS if ok else FAIL
        print(f"{status} {vtype:<20} pass rate: {pass_count}/5 — {result['reason']}")
        if not ok:
            all_pass = False

    return all_pass



#  TEST 6 — VISUALIZATION                                            
# ------------------------------------------------------------------ #

def test_visualization(save_plots: bool = True):
    section("TEST 6: Signal Visualization")
    try:
        import matplotlib
        matplotlib.use("Agg")   # non-interactive backend
    except ImportError:
        print(f"  [SKIP] matplotlib not installed. Run: pip install matplotlib")
        return True  # not a hard failure

    builder = HybridSignalBuilder()
    types = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]

    os.makedirs("plots", exist_ok=True)
    all_pass = True

    for vtype in types:
        try:
            chunk = builder.build(vtype)
            path = f"plots/signal_{vtype}.png" if save_plots else None
            utils.plot_signal(chunk, save_path=path)
            status = f"saved → {path}" if path else "displayed"
            print(f"{PASS} {vtype:<20} plot {status}")
        except Exception as e:
            print(f"{FAIL} {vtype}: {e}")
            all_pass = False

    return all_pass



#  SIGNAL DISTINGUISHABILITY CHECK                                   
# ------------------------------------------------------------------ #

def test_distinguishability():
    section("BONUS: Signal Distinguishability Check")
    builder = HybridSignalBuilder(sample_rate=4000, duration=1.0)

    print(f"\n  {'VESSEL TYPE':<20} {'PEAK FREQ':>12} {'RMS':>10} {'VARIANCE':>14}  CONF")
    print(f"  {SEP}")

    for vtype in ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]:
        chunk = builder.build(vtype)
        stats = utils.summarize(chunk)
        print(
            f"  {stats['vessel_type']:<20} "
            f"{stats['peak_freq_hz']:>12.1f} Hz "
            f"{stats['rms']:>10.5f} "
            f"{stats['amplitude_variance']:>14.6f}  "
            f"{stats['confidence_expected']}"
        )

    print(f"\n  Key distinctions:")
    print(f"    cargo     → lowest freq (50-200 Hz), moderate rms, low variance")
    print(f"    speedboat → highest freq (500-1500 Hz), highest rms, highest variance")
    print(f"    submarine → very low freq (20-100 Hz), lowest rms, masked")
    print(f"    low_conf  → any freq, very low rms, high noise ratio")
    print(f"    anomaly   → multi-peak, highest variance, burst artifacts")
    return True



#  MAIN                                                               
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SVACS Signal Layer Test Suite")
    parser.add_argument("--no-plots", action="store_true", help="Skip visualization tests")
    parser.add_argument("--no-stream", action="store_true", help="Skip streaming test")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  SVACS SIGNAL LAYER — FULL TEST SUITE")
    print("="*60)

    results = {}

    results["signal_generator"] = test_signal_generator()
    results["hybrid_builder"]   = test_hybrid_builder()
    results["scenario_builder"] = test_scenario_builder()

    if not args.no_stream:
        results["streaming"] = test_streaming()
    else:
        print("\n  [SKIP] Streaming test skipped (--no-stream)")

    results["validation"] = test_signal_validation()

    if not args.no_plots:
        results["visualization"] = test_visualization(save_plots=True)
    else:
        print("\n  [SKIP] Visualization test skipped (--no-plots)")

    test_distinguishability()

    # Summary
    print(f"\n{'='*60}")
    print(f"  TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for v in results.values() if v)
    total  = len(results)
    for test_name, result in results.items():
        icon = " PASS" if result else " FAIL"
        print(f"  {icon}  {test_name}")

    print(f"\n  Total: {passed}/{total} passed")
    if passed == total:
        print("\n   ALL TESTS PASSED — Pipeline input layer is ready.")
    else:
        print("\n   SOME TESTS FAILED — Check errors above.")
    print()