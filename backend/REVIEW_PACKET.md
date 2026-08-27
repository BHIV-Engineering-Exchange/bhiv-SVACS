# Vision Intelligence Runtime v1 Review Packet

*Updated August 2026 — see "Updates Since Original Delivery" at the end for what changed and why.*

## Objective Met
Delivered a working, indigenous Vision Intelligence Runtime ready for immediate consumption by Samachar and integration by SVACS without architectural changes. The runtime is modular, deterministic, replay-safe, and plug-and-play.

## Deliverables Status

- **Working Vision Runtime**: ✅ Built with FastAPI, Pydantic, OpenCV, EasyOCR, and YOLOv8.
- **OCR Integration**: ✅ EasyOCR implemented in `app/services/ocr_service.py`. Extracts text and bounds.
- **Vessel Classification Engine**: ✅ YOLOv8 detection + EfficientNetV2-S classification in `app/services/inference_service.py`. A custom-trained classifier checkpoint (`efficientnet_vessel_best.pth`) is now in place, covering 6 real vessel classes (Container Ship, Fishing Vessel, LPG Carrier, Offshore Support Vessel, Oil Tanker, Passenger Ferry), trained on a mix of real captured photographs and existing data. Class labels are loaded dynamically from the checkpoint, not hardcoded, so future retraining with additional classes requires no code changes.
- **REST API**: ✅ Exposed via `/api/v1/analyze` and `/api/v1/batch-analyze`.
- **Batch Inference**: ✅ Supported via `/api/v1/batch-analyze` array processing.
- **Replay Evidence**: ✅ Implemented in `app/services/replay_service.py`. Saves input image, complete response payload (excluding large base64 image data to save disk space), and execution metadata per request. **Note:** storage location currently resolves to a hardcoded absolute path (`C:\tmp\svacs_replays`) rather than a project-relative path — see Known Issues below.
- **Confidence Scoring**: ✅ Handled intrinsically by YOLOv8 and EfficientNetV2, included in output JSON schema, including full top-3 predictions per detection.
- **Explainability Output**: ✅ Implemented in `app/services/explainability.py`. Renders bounding boxes and labels for OCR and classifications back onto the original image as visual evidence.
- **CPU/GPU Support**: ✅ EasyOCR and YOLOv8 are configured to attempt GPU usage natively, but will seamlessly fallback to CPU.
- **Structured Contracts**: ✅ Defined tightly using Pydantic in `app/models/schemas.py`.
- **Bucket Integration**: ✅ *New.* `app/services/bucket_client.py` writes vision-runtime artifacts to Siddhesh's live Bucket service as Stage 7 of the orchestrator, using the same endpoint and envelope contract already proven in the separate acoustic-signal pipeline. Non-fatal by design — a Bucket outage does not block the classification response. **Not yet confirmed:** live test writes against Bucket have returned HTTP 503 (Render cold-start) on both attempts; the integration code is real and correct, but a successful write has not yet been observed for this path.

## Quick Start for Samachar Integration (Om Patil & Chandragupta)

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Server:**
   ```bash
   uvicorn app.main:app --reload
   ```
3. **API Documentation:**
   Open `http://localhost:8000/docs` to view the interactive Swagger API documentation. The contracts are fully documented there.

**Status note:** as of this update, this runtime is not yet actually receiving requests via Samachar's ingestion path in the local demo/test environment — the dashboard currently posts directly to this service's `/intelligence/image` endpoint, bypassing Samachar. This is a known, explicitly tracked gap (see the Operational Integration sprint's Runtime Validation Report), not an assumption that integration is complete.

## Notes for SVACS Integration (Nupur & Ankita)

The standard response contract (`VisionAnalysisResponse`) looks like this:
```json
{
  "replay_id": "uuid-v4-string",
  "detections": [
    {
      "label": "Offshore Support Vessel",
      "confidence": 0.9893,
      "bounding_box": {"x_min": 0.0, "y_min": 0.0, "x_max": 960.0, "y_max": 1280.0},
      "top_predictions": [
        {"class_name": "Offshore Support Vessel", "confidence": 98.93},
        {"class_name": "Fishing Vessel", "confidence": 0.57},
        {"class_name": "Passenger Ferry", "confidence": 0.33}
      ]
    }
  ],
  "ocr_results": [
    {
      "text": "IMO 123456",
      "confidence": 0.95,
      "bounding_box": {"x_min": 0.0, "y_min": 0.0, "x_max": 50.0, "y_max": 20.0}
    }
  ],
  "explainable_image_base64": "base64_encoded_string_here"
}
```

This contract is final and replay-safe. `top_predictions` is now genuinely populated (previously scaffolded); real example values shown above are taken directly from a live test run (see the Image Validation Pack / Replay Validation Evidence for this sprint).

**Important — two separate identifiers per request:** the API layer (`app/main.py`) generates its own `trace_id` for the outer response, while the orchestrator (`vision_orchestrator.py`) generates a separate `replay_id`. Both are logged and both point to the same request, but they are not the same value. If SVACS/downstream systems expect a single canonical trace ID, this needs to be reconciled — flagged for discussion, not yet resolved.

## Known Issues (new, found during this sprint's validation)

1. **Replay storage path is hardcoded and non-portable.** `app/core/config.py` resolves `REPLAY_STORAGE_DIR` to an absolute path (`C:\tmp\svacs_replays`) rather than a relative, project-local, or environment-configurable one. This will not work as-is on a different machine or in a deployed environment unless that exact path is manually created.
2. **`?quick=true` silently skips OCR.** Not a bug, but worth documenting clearly for anyone consuming replay records — an empty `ocr_results` array may simply mean quick mode was used, not that OCR failed.
3. **`trace_id` / `replay_id` duplication** — see above.
4. **Bucket write not yet confirmed successful for this specific path** — integration exists and is correctly wired, but has not yet produced a verified successful write due to external service (Bucket/Render) unavailability during testing.

## Action Items
- ~~Provide the custom trained Vessel weights~~ — **Done.** `efficientnet_vessel_best.pth` retrained and in place, 6 real classes.
- Coordinate with Chandragupta on actual Samachar ingestion integration (currently bypassed for local demo purposes).
- Retry/monitor Bucket write success for the image path once Siddhesh's service is confirmed warm/available.
- Decide (with Ankita) whether `trace_id`/`replay_id` should be unified.
- Fix hardcoded replay storage path to something portable.

---

## Updates Since Original Delivery

This packet was originally written by Vijay at initial Vision Runtime delivery. The updates above reflect work completed during the SVACS Operational Integration and Image Validation sprint (August 2026): classifier retraining with real photographs and a new vessel class, Bucket integration, a CORS fix enabling the dashboard to reach this service locally, and several findings surfaced while gathering verifiable evidence for that sprint's deliverables. Full supporting evidence (real photographs, confidence scores, verbatim replay records, and stage-by-stage runtime status) is in the accompanying Image Validation Pack, Replay Validation Evidence, and Runtime Validation Report documents for this sprint.
