# SVACS — Replay Validation Evidence & End-to-End Trace Evidence

**Author:** Nupur Gavane
**Sprint:** SVACS Operational Integration and Image Validation
**Scope:** Deliverables 5 (End-to-End Trace Evidence) and 6 (Replay Validation Evidence)
**Date:** August 2026

---

## Purpose

This document provides verbatim evidence that the SVACS Vision Runtime's replay mechanism (`replay_service.py`) genuinely persists a complete, reconstructable record for every image processed, keyed by a stable `replay_id` that also functions as the request's trace identifier end-to-end.

All evidence below was pulled directly from disk, not reconstructed from memory or logs, using the actual `contract.json` and `metadata.json` files written by the running system during today's local test session.

---

## Storage Location — Important Finding

Replay artifacts are **not** stored inside the project directory. `backend/app/core/config.py` resolves `REPLAY_STORAGE_DIR` to an **absolute, hardcoded path**:

```
C:\tmp\svacs_replays
```

This was discovered during evidence-gathering for this document: searches for known replay UUIDs under `backend/` and under `C:\Projects` both returned nothing, until the actual resolved path was queried directly:

```powershell
python -c "from app.core.config import settings; import os; print(os.path.abspath(settings.REPLAY_STORAGE_DIR))"
# → C:\tmp\svacs_replays
```

**Flagged as a portability risk:** this path is specific to the current machine and will not exist on a fresh clone, a different developer's machine, or in a containerized/deployed environment unless explicitly created or configured. Recommend making this a relative, project-local path (e.g. `backend/replays/`) or an explicit environment variable with a safe default, before this is relied upon as production evidence storage.

Note: `backend/replays/` (inside the repo) does contain ~200 pre-existing UUID folders, but these were confirmed to be artifacts from Vijay's own earlier local testing (metadata timestamps from July 2026, `yolo_model` path pointing to `C:\Users\vijay\Downloads\...`) — not from this session's testing, and not evidence for this pack.

---

## Evidence Record 1

**Corresponds to:** Image Validation Pack, Case 1 (`osv_1.jpeg`)

**File:** `C:\tmp\svacs_replays\16984279-c12c-41c9-8edb-b935b7bf4128\contract.json`

```json
{
    "replay_id": "16984279-c12c-41c9-8edb-b935b7bf4128",
    "detections": [
        {
            "label": "Offshore Support Vessel",
            "confidence": 0.9893000000000001,
            "bounding_box": {
                "x_min": 0.0,
                "y_min": 0.0,
                "x_max": 960.0,
                "y_max": 1280.0
            },
            "top_predictions": [
                { "class_name": "Offshore Support Vessel", "confidence": 98.93 },
                { "class_name": "Fishing Vessel", "confidence": 0.57 },
                { "class_name": "Passenger Ferry", "confidence": 0.33 }
            ]
        }
    ],
    "ocr_results": [],
    "explainable_image_base64": null
}
```

**File:** `C:\tmp\svacs_replays\16984279-c12c-41c9-8edb-b935b7bf4128\metadata.json`

```json
{
    "timestamp": "2026-08-26T13:00:07.605290",
    "model_version": "1.0.0",
    "yolo_model": "C:\\Projects\\bhiv-SVACS-latest\\backend\\vessel_front_model.pt"
}
```

**Corresponding server log (same request, same `replay_id`):**
```
Stage 1 (preprocessing) OK
Stage 2 (OCR) OK — 0 results  [quick=true, OCR skipped by design]
Stage 3 (detection) OK — 1 detection(s)
Stage 4 (explainability) OK
Stage 6 (replay save) OK — replay_id=16984279-c12c-41c9-8edb-b935b7bf4128
Stage 7 (bucket write) FAILED (non-fatal): HTTP 503
POST /intelligence/image completed — trace_id=e86358cb-2ed2-4459-825f-f06c02ce4408 vessel_class=Offshore Support Vessel
```

**Trace continuity note:** the outer HTTP response's `trace_id` (`e86358cb-...`) and the inner `replay_id` (`16984279-...`) are **two distinct identifiers generated within the same request** — `trace_id` by `app/main.py`'s handler, `replay_id` by `vision_orchestrator.py`. Both are logged and both are traceable back to this single request, but they are not the same value. This should be clarified or unified if a single canonical trace identifier is required for downstream consumers (e.g. Bucket, TANTRA).

---

## Evidence Record 2

**Corresponds to:** Image Validation Pack, Case 4 (`cordelia-cruise-2.jpeg`)

**File:** `C:\tmp\svacs_replays\f9f4f9cc-add9-4f16-b824-77f321853f1b\contract.json`

```json
{
    "replay_id": "f9f4f9cc-add9-4f16-b824-77f321853f1b",
    "detections": [
        {
            "label": "Passenger Ferry",
            "confidence": 0.9989,
            "bounding_box": {
                "x_min": 0.0,
                "y_min": 0.0,
                "x_max": 1200.0,
                "y_max": 900.0
            },
            "top_predictions": [
                { "class_name": "Passenger Ferry", "confidence": 99.89 },
                { "class_name": "Oil Tanker", "confidence": 0.04 },
                { "class_name": "LPG Carrier", "confidence": 0.03 }
            ]
        }
    ],
    "ocr_results": [],
    "explainable_image_base64": null
}
```

**File:** `C:\tmp\svacs_replays\f9f4f9cc-add9-4f16-b824-77f321853f1b\metadata.json`

```json
{
    "timestamp": "2026-08-26T11:32:43.797836",
    "model_version": "1.0.0",
    "yolo_model": "C:\\Projects\\bhiv-SVACS-latest\\backend\\vessel_front_model.pt"
}
```

**Note on empty `ocr_results`:** this request used `?quick=true`, which skips OCR by design. A separate, non-quick invocation of the same source image on an earlier date did produce OCR output (partial hull text `'CORDEEA'`), but that result is stored under a different `replay_id` from a different session and is not part of this evidence record.

---

## Findings

1. **Replay persistence is real and independently verifiable.** Both evidence records above were retrieved directly from disk, matching exactly what the corresponding server logs reported at request time — no discrepancy between logged claim and stored artifact.
2. **Two distinct identifiers exist per request** (`trace_id` at the API layer, `replay_id` at the orchestrator layer). Functionally this doesn't break traceability — both are logged and both point to the same request — but it is not a single unified trace ID, which the sprint's "trace continuity" acceptance criterion may expect. Worth raising with Ankita (owns the SVACS runtime/trace design) before this is considered fully compliant.
3. **Replay storage location is a hard-coded absolute path** (`C:\tmp\svacs_replays`) rather than a project-relative or configurable one — a genuine portability gap for anyone else running this system, or for eventual deployment.
4. **`?quick=true` mode silently disables OCR.** This is by design, not a bug, but it means OCR evidence is inconsistently available depending on which endpoint variant is called — worth documenting clearly for anyone consuming these replay records downstream, so an absent OCR result isn't mistaken for an OCR failure.
5. **Bucket write is not yet part of the replay-verifiable chain for the image path.** Both live attempts today failed (HTTP 503). The replay artifact itself is confirmed durable regardless of Bucket's availability, since Stage 6 (Replay) completes and saves before Stage 7 (Bucket) is even attempted — this is a resilient design, but it means Bucket-backed provenance for images is not yet demonstrated, only attempted.
