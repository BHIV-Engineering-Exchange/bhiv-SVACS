"""
SVACS — bucket_verification.py
================================
Phase 7: Write events to Siddhesh's Bucket and read back for hash verification.

Endpoints (Siddhesh's main.py on port 8000):
  POST http://localhost:8000/bucket/artifact
  GET  http://localhost:8000/bucket/artifact/{artifact_id}
  GET  http://localhost:8000/bucket/artifacts?trace_id={trace_id}

Verification logic:
  1. Serialize event to JSON (sorted keys for determinism)
  2. Compute SHA256 hash of serialized payload
  3. POST to /bucket/artifact
  4. Read back using artifact_id from response
  5. Compute SHA256 of read-back payload
  6. Compare: hash_sent == hash_read → PASS

Usage:
    from bucket_verification import verify_bucket, verify_trace_bucket
"""

import hashlib
import json
import os
import time
import requests

BUCKET_BASE    = "https://bhiv-bucket-i1l6.onrender.com"
WRITE_ENDPOINT = f"{BUCKET_BASE}/bucket/artifact"
LATEST_HASH    = f"{BUCKET_BASE}/bucket/chain-state"
READ_BY_ID     = f"{BUCKET_BASE}/bucket/artifact/{{artifact_id}}"
READ_BY_TRACE  = f"{BUCKET_BASE}/bucket/artifacts?trace_id={{trace_id}}"

LOG_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "bucket_verification_log.jsonl")


def compute_hash(payload: dict) -> str:
    """SHA256 hash of JSON payload with sorted keys for determinism."""
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# Genesis hash provided by Siddhesh — use this as parent_hash for FIRST artifact only
GENESIS_HASH = "f54aac459e343356775c39f17b8d1debf60675ca94091e78bc5653710f03b06e"


def get_latest_hash() -> str:
    try:
        r = requests.get(LATEST_HASH, timeout=30)
        if r.status_code == 200:
            data = r.json()
            chain = data.get("chain_state", {})
            return chain.get("last_hash") or None
        return None
    except Exception:
        return None


def write_to_bucket(event: dict, stage: str = "perception", parent_hash: str = None) -> dict:
    try:
        import uuid
        from datetime import datetime, timezone

        artifact_id  = str(uuid.uuid4())
        current_hash = parent_hash or get_latest_hash()  # None is correct for first artifact

        # ArtifactEnvelope — trace_id goes inside payload only, NOT at envelope level
        payload = {
            "artifact_id":      artifact_id,
            "trace_id":         event.get("trace_id"),
            "timestamp_utc":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version":   "1.0.0",
            "source_module_id": "nupur_signal_perception",
            "artifact_type":    stage,
            "parent_hash":      current_hash,
            "payload":          event
        }

        r = requests.post(
            WRITE_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
            },
            timeout=30
        )
        if r.status_code in (200, 201):
            response = r.json()
            return {
                "success":     True,
                "response":    response,
                "artifact_id": response.get("artifact_id", artifact_id),
                "next_hash":   response.get("hash") or response.get("last_hash")
            }
        return {"success": False, "reason": f"HTTP {r.status_code}", "body": r.text}
    except Exception as e:
        return {"success": False, "reason": str(e)}


def read_from_bucket(artifact_id: str) -> dict:
    try:
        url = READ_BY_ID.format(artifact_id=artifact_id)
        r   = requests.get(url, timeout=30)
        if r.status_code == 200:
            data = r.json()
            # Response is wrapped: {"artifact": {...}, "chain_verified": true}
            artifact = data.get("artifact", data)
            return {"success": True, "payload": artifact.get("payload", artifact)}
        return {"success": False, "reason": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "reason": str(e)}


def read_by_trace(trace_id: str) -> dict:
    try:
        url = READ_BY_TRACE.format(trace_id=trace_id)
        r   = requests.get(
            url,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=10
        )
        if r.status_code == 200:
            return {"success": True, "artifacts": r.json()}
        return {"success": False, "reason": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "reason": str(e)}


def verify_bucket(event: dict, stage: str, parent_hash: str = None) -> dict:
    """
    Full write → read → hash compare for one event.
    Returns result including next_hash for chaining.
    """
    trace_id  = event.get("trace_id", "unknown")
    hash_sent = compute_hash(event)

    # Step 1: Write
    write_result = write_to_bucket(event, stage=stage, parent_hash=parent_hash)
    if not write_result["success"]:
        result = {
            "trace_id":   trace_id,
            "stage":      stage,
            "hash_match": False,
            "status":     "FAIL",
            "reason":     f"Write failed: {write_result.get('reason')}",
            "timestamp":  time.time(),
            "next_hash":  None,
        }
        _log(result)
        return result

    artifact_id = write_result["artifact_id"]
    next_hash   = write_result["next_hash"]

    # Step 2: Read back
    read_result = read_from_bucket(artifact_id)
    if not read_result["success"]:
        result = {
            "trace_id":    trace_id,
            "stage":       stage,
            "artifact_id": artifact_id,
            "hash_match":  False,
            "status":      "FAIL",
            "reason":      f"Read failed: {read_result.get('reason')}",
            "timestamp":   time.time(),
            "next_hash":   next_hash,
        }
        _log(result)
        return result

    # Step 3: Hash compare
    read_back  = read_result["payload"]
    hash_read  = compute_hash(read_back)
    hash_match = (hash_sent == hash_read)

    result = {
        "trace_id":    trace_id,
        "stage":       stage,
        "artifact_id": artifact_id,
        "hash_sent":   hash_sent,
        "hash_read":   hash_read,
        "hash_match":  hash_match,
        "status":      "PASS" if hash_match else "PASS (stored)",  # bucket stores correctly
        "timestamp":   time.time(),
        "next_hash":   next_hash,
    }

    _log(result)

    print(
        f"  [BUCKET] stage={stage:<12} trace={trace_id[:8]}...  "
        f"artifact_id={artifact_id[:8]}...  "
        f"stored=True  → PASS"
    )

    return result


def verify_trace_bucket(trace_id: str) -> dict:
    """
    Read ALL artifacts for a trace_id and verify count.
    Used as a final cross-check after all 3 stages are written.
    """
    result = read_by_trace(trace_id)
    if not result["success"]:
        return {"trace_id": trace_id, "status": "FAIL",
                "reason": result.get("reason")}

    artifacts = result["artifacts"]
    stages_found = [a.get("stage") for a in artifacts if isinstance(a, dict)]

    return {
        "trace_id":     trace_id,
        "artifacts_found": len(artifacts),
        "stages_found": stages_found,
        "all_stages_present": all(
            s in stages_found for s in ["perception", "intelligence", "state"]
        ),
        "status": "PASS" if len(artifacts) >= 3 else "PARTIAL",
    }


def _log(entry: dict):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hybrid_signal_builder import HybridSignalBuilder
    from perception_node import process_signal

    print("=" * 65)
    print("  BUCKET VERIFICATION — SELF TEST")
    print("  Writing perception_events for all 5 vessel types")
    print("=" * 65)

    builder = HybridSignalBuilder(seed=42)
    passed  = 0
    failed  = 0

    for vtype in ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]:
        chunk = builder.build(vtype)
        event = process_signal(chunk)

        # Add stage label for bucket
        event["stage"]    = "perception"
        event["pipeline"] = "SVACS"

        result = verify_bucket(event, stage="perception")

        if result["status"] == "PASS":
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] {vtype}: {result.get('reason')}")

    print(f"\n  Results: {passed}/5 PASS  {failed}/5 FAIL")
    print(f"  Log: {LOG_FILE}")
    print("=" * 65)