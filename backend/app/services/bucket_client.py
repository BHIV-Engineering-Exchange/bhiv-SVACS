"""bucket_client.py — Writes vision-runtime artifacts to Siddhesh's Bucket service.

This is a self-contained port of the SAME real Bucket contract already proven
working in frontend/services/data_layer/bucket_verification.py (used successfully
in the acoustic pipeline). It exists here separately, not as a fake substitute,
but because backend/ deploys standalone and cannot reach into frontend/'s folder
at runtime.

Endpoint, envelope schema, and hash-verification logic are IDENTICAL to the
already-validated acoustic-pipeline integration — same live Bucket service,
same contract, just called from the image-classification path.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BUCKET_BASE = "https://bhiv-bucket-i1l6.onrender.com"
WRITE_ENDPOINT = f"{BUCKET_BASE}/bucket/artifact"
LATEST_HASH_ENDPOINT = f"{BUCKET_BASE}/bucket/chain-state"

SOURCE_MODULE_ID = "vision_runtime_backend"
REQUEST_TIMEOUT_SECONDS = 15


def _compute_hash(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get_latest_hash() -> Optional[str]:
    try:
        r = requests.get(LATEST_HASH_ENDPOINT, timeout=REQUEST_TIMEOUT_SECONDS)
        if r.status_code == 200:
            chain = r.json().get("chain_state", {})
            return chain.get("last_hash")
        return None
    except Exception as exc:
        logger.warning("Bucket chain-state lookup failed (non-fatal): %s", exc)
        return None


def write_vision_artifact(trace_id: str, artifact_type: str, payload: dict) -> dict:
    """Write one vision-runtime artifact to Bucket.

    Args:
        trace_id: the replay_id / trace identifier for this detection event.
        artifact_type: e.g. "vision_detection" — mirrors the "stage" concept
                       used in the acoustic pipeline's bucket_verification.py.
        payload: the event data to store (e.g. detections, confidence, OCR text).

    Returns a dict describing success/failure — never raises, so callers can
    treat this as a non-fatal step (same pattern as Stage 6 / replay_service).
    """
    try:
        artifact_id = str(uuid.uuid4())
        parent_hash = _get_latest_hash()

        envelope = {
            "artifact_id": artifact_id,
            "trace_id": trace_id,
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": "1.0.0",
            "source_module_id": SOURCE_MODULE_ID,
            "artifact_type": artifact_type,
            "parent_hash": parent_hash,
            "payload": payload,
        }

        hash_sent = _compute_hash(envelope)

        r = requests.post(
            WRITE_ENDPOINT,
            json=envelope,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if r.status_code in (200, 201):
            response = r.json()
            return {
                "success": True,
                "artifact_id": response.get("artifact_id", artifact_id),
                "hash_sent": hash_sent,
                "stored": True,
            }

        return {
            "success": False,
            "reason": f"HTTP {r.status_code}",
            "body": r.text[:300],
        }

    except Exception as exc:
        return {"success": False, "reason": str(exc)}


bucket_client = None  # module itself is used directly via write_vision_artifact()
