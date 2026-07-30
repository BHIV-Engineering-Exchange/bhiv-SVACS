"""
SVACS — stress_test.py
=======================
PHASE 5 | Concurrent Stress Test

Runs 3 threads simultaneously, each sending 20 chunks.
Total: 60 chunks under concurrent load.
Validates: no crashes, all HTTP 200, no data corruption.

Run from: services/data_layer/
  python stress_test.py

Output: phase5_stress_test_log.txt
"""

import os, sys, json, time, threading
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import requests
from hybrid_signal_builder import HybridSignalBuilder

ENDPOINT = "http://localhost:8000/ingest/signal"
LOG_FILE = os.path.join(BASE_DIR, "phase5_stress_test_log.txt")

lines      = []
lines_lock = threading.Lock()

def log(msg=""):
    print(msg)
    with lines_lock:
        lines.append(str(msg))

log("=" * 65)
log("  SVACS — PHASE 5: STRESS TEST")
log(f"  Endpoint : {ENDPOINT}")
log(f"  Threads  : 3  |  Chunks per thread: 20  |  Total: 60")
log(f"  Run at   : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
log("=" * 65)

# Shared counters
results      = []
results_lock = threading.Lock()

def send_burst(thread_id, n=20):
    builder    = HybridSignalBuilder(4000, 1.0)
    vessels    = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]
    local_pass = 0
    local_fail = 0

    for i in range(n):
        vtype = vessels[i % len(vessels)]
        chunk = builder.build(vtype)
        try:
            r    = requests.post(ENDPOINT, json=chunk, timeout=5)
            ok   = (r.status_code == 200)
            resp = r.json()
            tid_match = resp.get("trace_id") == chunk["trace_id"]

            if ok and tid_match:
                local_pass += 1
                log(f"  [T{thread_id}] chunk {i+1:02d} -> HTTP {r.status_code} | vessel={vtype:<16} | trace={'OK' if tid_match else 'MISMATCH'}")
            else:
                local_fail += 1
                log(f"  [T{thread_id}] chunk {i+1:02d} -> HTTP {r.status_code} FAIL | trace={'OK' if tid_match else 'MISMATCH'}")

        except Exception as e:
            local_fail += 1
            log(f"  [T{thread_id}] chunk {i+1:02d} -> ERROR: {e}")

    with results_lock:
        results.append({
            "thread_id":   thread_id,
            "sent":        n,
            "passed":      local_pass,
            "failed":      local_fail,
        })
    log(f"\n  [T{thread_id}] Done — {local_pass}/{n} passed")


# Run 3 threads concurrently
threads = [threading.Thread(target=send_burst, args=(i,)) for i in range(3)]
start   = time.time()
for t in threads: t.start()
for t in threads: t.join()
elapsed = time.time() - start

# Summary
total_sent   = sum(r["sent"]   for r in results)
total_passed = sum(r["passed"] for r in results)
total_failed = sum(r["failed"] for r in results)
overall      = (total_failed == 0)

log(f"\n{'=' * 65}")
log("  STRESS TEST SUMMARY")
log(f"{'=' * 65}")
log(f"  Total chunks sent   : {total_sent}")
log(f"  Passed (HTTP 200)   : {total_passed}")
log(f"  Failed              : {total_failed}")
log(f"  Elapsed time        : {elapsed:.2f}s")
log(f"  Throughput          : {total_sent/elapsed:.1f} chunks/sec")

if overall:
    log("\n  [PASS] STRESS TEST PASSED")
    log("  Server handled concurrent load without errors.")
else:
    log(f"\n  [FAIL] {total_failed} chunks failed under concurrent load")

log("=" * 65)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\n[LOG SAVED] -> {LOG_FILE}")
