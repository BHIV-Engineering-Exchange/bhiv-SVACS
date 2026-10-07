# Vision Intelligence Runtime - Review Packet

Originally delivered by Vijay at initial Vision Runtime delivery. Updated August 2026 (Operational Integration and Image Validation sprint) and October 2026 (Phase 2: Advanced Integration & Security Hardening). See "Updates Since Original Delivery" at the end for what changed and why. Detailed evidence for the October update is in `operational_integration_sprint/PHASE2_COMPLETION_REPORT.md`.

## Objective Met
Delivered a working, indigenous Vision Intelligence Runtime ready for consumption by Samachar and integration by SVACS without architectural changes. The runtime is modular, replay-safe and plug-and-play. Determinism was verified in October 2026: the same image returned an identical response across 5 runs on the real models, including the first request that loaded them (every field compared, largest numeric difference 0; one image, one machine, CPU inference). The comparison after a server restart is reported in the Phase 2 report, section 2.3.

## Deliverables Status

- **Working Vision Runtime:** Done. Built with FastAPI, Pydantic, OpenCV, EasyOCR and YOLOv8.
- **OCR Integration:** Done. EasyOCR in `app/services/ocr_service.py`. Extracts text and bounds.
- **Vessel Classification Engine:** Done. YOLOv8 detection plus EfficientNetV2-S classification in `app/services/inference_service.py`. Class labels are loaded dynamically from the checkpoint, not hardcoded.
  - **Current checkpoint (October 2026): 21 classes** - 20 Indian Navy classes plus `OSV Class`.
    - Aircraft carriers: Vikrant, Vikramaditya.
    - Destroyers: Visakhapatnam Class, Kolkata Class, Delhi Class, Rajput Class.
    - Frigates: Nilgiri Class, Shivalik Class, Talwar Class, Brahmaputra Class.
    - Submarines: Arihant Class, Kalvari Class, Shishumar Class, Sindhughosh Class.
    - Corvettes: Arnala Class, Mahe Class, Kamorta Class, Kora Class, Khukri Class, Veer Class.
  - **The civilian classes of the August checkpoint (Container Ship, Fishing Vessel, LPG Carrier, Oil Tanker, Passenger Ferry) are not in the current checkpoint.** A decision was taken to train a separate naval model that keeps only `OSV Class` from the earlier data. The classifier can only answer with one of its 21 classes, so those civilian vessel types will not be recognised as their true type. If civilian coverage is required, a second classifier or a combined retraining is needed.
  - Training data: 3,819 images, 61 to 461 per class (ratio 7.6 to 1), trained with a weighted sampler and weighted loss to offset the imbalance.
  - **Accuracy figure: unrecorded.** The best validation accuracy of the 21-class run was not retained and cannot be reconstructed (the checkpoint stores only weights and class names, and the training split was random and not saved). A held-out evaluation on photographs never used in training is still to be done.
- **REST API:** Done. `/api/v1/analyze` and `/api/v1/batch-analyze` (original contract), plus two endpoints added later: `/intelligence/image` (used by the dashboard; richer response, see below) and `/naval/identify` (matching from typed-in details, no image needed).
- **Batch Inference:** Done via `/api/v1/batch-analyze`.
- **Replay Evidence:** Done in `app/services/replay_service.py`. Saves the input image, the complete response payload (excluding the large base64 image) and execution metadata per request. **Note:** the storage location resolves to a hardcoded absolute path (`C:\tmp\svacs_replays`); see Known Issues.
- **Confidence Scoring:** Done. Included in the output JSON, with the top-3 predictions per detection.
- **Explainability Output:** Done in `app/services/explainability.py`. Draws bounding boxes and labels for OCR and classifications onto the original image.
- **CPU/GPU Support:** Done. EasyOCR and YOLOv8 attempt GPU use and fall back to CPU.
- **Structured Contracts:** Done for `/api/v1/analyze` (Pydantic, `app/models/schemas.py`). `/intelligence/image` declares no response model, so its response is not described in the generated API documentation (see Known Issues).
- **Bucket Integration:** Done and confirmed. `app/services/bucket_client.py` writes one artifact per processed image to the Bucket service as Stage 7 of the orchestrator. Each artifact carries the detections and OCR results (not the image), filed under the orchestrator's `replay_id`. Non-fatal by design: a Bucket outage does not block the classification response.
  - Confirmed on 2026-10-07: Bucket's own `artifact_count` rose from 22 to 27 for five uploads, and `/bucket/status` reported 100 percent synced with no failed writes. Earlier attempts in August returned HTTP 503, consistent with the free-tier service waking from idle.
  - Limits: the write is not read back, there is no retry or queue (a failed write is logged and that image's record is not stored later), and the write is made inside the request, adding about 3.3 s (median) to each upload.
- **Naval Knowledge and Ship Identification (added October 2026):** A knowledge pack of 20 classes (dimensions, role, risk level) in `maritime_knowledge/indian_naval_knowledge_pack.json`, and a ship registry of 77 ships with hull pennant numbers in `maritime_knowledge/ship_registry.json`. Individual ships are named only by reading the hull pennant number with OCR; when it is not legible the class roster is returned with no confidence values. A cross-check flags a possible misclassification when the pennant's prefix letter contradicts the predicted vessel type. Both data files exist in two copies (repo root and `backend/`); a test fails if they differ.
- **Multi-Vessel Output (added October 2026):** Each detected ship is cropped and returned with its own label, confidence, ship identification and misclassification check.
- **Authentication (added October 2026):** Every POST endpoint requires the header `X-API-Key` when the environment variable `SVACS_API_KEY` is set (401 if missing, 403 if wrong). If the variable is not set the endpoints stay open and a warning is logged at startup.
- **Monitoring (added October 2026):** `/health`, `/stage-metrics`, `/bucket/status`, `/validation-breakdown` and the new `/metrics` report live values measured from real traffic. Previously they returned fixed invented numbers.

## Quick Start for Samachar Integration (Om Patil & Chandragupta)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Set an API key (recommended on any shared machine):**
   ```powershell
   $env:SVACS_API_KEY = "your-key"
   ```
   Callers then send it as the `X-API-Key` header. The dashboard reads the same value from `VITE_API_KEY` in `frontend/.env.local` (kept out of git).
3. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```
4. **API documentation:** open `http://localhost:8000/docs` for the interactive Swagger documentation.
5. **Run the tests:**
   ```bash
   pip install pytest "httpx<0.28"
   python -m pytest tests -q
   ```
   The `httpx` pin is needed with Starlette 0.36.3.

**Status note:** as of this update the runtime is still not receiving requests through Samachar's ingestion path. The dashboard posts directly to this service's `/intelligence/image` endpoint, bypassing Samachar. This is a known, explicitly tracked deviation from the published contract, not an assumption that integration is complete.

## Notes for SVACS Integration (Nupur & Ankita)

The standard response contract for `/api/v1/analyze` (`VisionAnalysisResponse`) is unchanged:
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
The example values come from the August checkpoint; the field structure is current. The class names in a response now come from the 21-class checkpoint.

**`/intelligence/image` response** (used by the dashboard). The headline fields describe the single largest detection; per-ship results are in `ship_crops`.
- Headline: `trace_id`, `validation_status` (OK or FLAG), `vessel_detected`, `vessel_class`, `confidence_score`, `ocr_text`, `operator`, `risk_level`, `classification_source`, `detections`, `top_predictions`, `explanation`, `explainable_image_base64`.
- Per ship: `ship_crops`, a list with `detection_id`, `label`, `confidence`, `bounding_box`, `crop_image_url`, `ship_identification` and `pennant_type_check`.
- Optional matching from typed-in details: `naval_knowledge_candidates`, `naval_knowledge_note`.
- Headline copies of `ship_identification` and `pennant_type_check` for the largest detection.

**Important - two separate identifiers per request:** `/api/v1/analyze` returns the orchestrator's `replay_id`. `/intelligence/image` returns the API layer's `trace_id`, and stores the crop images under it, while the replay record is stored under the `replay_id`, which is logged but not returned by that endpoint. They are different values for the same request, and the Bucket artifact is filed under the `replay_id`, so the trace ID shown in the dashboard cannot be used to find its Bucket record. If SVACS expects a single canonical trace ID this must be reconciled; the decision is still open.

## Known Issues

1. **Replay storage path is hardcoded and non-portable.** `app/core/config.py` resolves `REPLAY_STORAGE_DIR` to `C:\tmp\svacs_replays`. It will not work on another machine or a deployed environment unless that path exists.
2. **`?quick=true` skips detection and OCR.** In quick mode the YOLO detector is not loaded: the whole image is classified as one object (one box covering the full image) and OCR is skipped. It cannot return several ships. The dashboard no longer uses it. It was added to avoid a request timeout on the hosted service, so using the full pipeline there may bring that timeout back.
3. **`trace_id` / `replay_id` duplication.** See above.
4. **Bucket:** write confirmed, but no read-back, no retry, and the write adds about 3.3 s to each upload.
5. **Civilian classes removed from the checkpoint** (see Deliverables Status). Entries for them remain in `CIVILIAN_RISK_LEVELS` in `main.py` and are now unreachable except `OSV Class`.
6. **No response model for `/intelligence/image`**, so its response is absent from the generated API documentation and no schema test exists.
7. **Samachar bypassed** (see Status note).
8. **Headline result follows the largest detection, not the most confident one.** With several ships the per-ship cards are the accurate result.
9. **Sister ships cannot be told apart visually.** Ship names rely on a legible pennant number.
10. **Model accuracy unrecorded; no held-out evaluation.**
11. **Authentication limits.** A shared secret, not user login. The dashboard sends it from the browser, so anyone who can load the dashboard can read it. GET endpoints (including `/metrics` and `/vessels`) and the artifact images are open. There is no rate limiting and no upload size limit.
12. **Metrics are in memory, per process.** A restart resets them. Latency and status use 5-minute windows, so an idle server shows 0.0 with a sample count of 0, which means "no data", not "instant".
13. **First request after start is slow** (about 19 s measured) because the models load on demand.

## Action Items
- Coordinate with Chandragupta on actual Samachar ingestion (currently bypassed).
- Decide with Ankita whether `trace_id` and `replay_id` should be unified.
- Fix the hardcoded replay storage path.
- Add Bucket read-back verification, and consider moving the write off the request path (Siddhesh).
- Run a held-out evaluation of the classifier and record the result (Vijay).
- Decide whether civilian vessel classes must be recognised, and if so retrain or add a second classifier.
- Declare a response model for `/intelligence/image` and add a schema test.
- Add an upload size limit and rate limiting; replace the shared key with user-level authentication before any shared deployment.
- Done: custom trained weights in place; Bucket write confirmed; unit and data-integrity tests (172); authentication; live monitoring.

---

## Updates Since Original Delivery

This packet was originally written by Vijay at initial Vision Runtime delivery.

**August 2026** (SVACS Operational Integration and Image Validation sprint): classifier retraining with real photographs and a new vessel class, Bucket integration, a CORS fix enabling the dashboard to reach this service locally, and several findings from gathering evidence for that sprint's deliverables. Supporting evidence is in the Image Validation Pack, Replay Validation Evidence and Runtime Validation Report.

**October 2026** (Phase 2: Advanced Integration & Security Hardening): the classifier was retrained as a 21-class naval model (see the note on civilian classes); naval knowledge pack, ship registry, OCR-based ship identification and the pennant cross-check were added; multi-vessel output with per-ship crops; API key authentication; live monitoring; a 172-test suite; a determinism check; confirmation that Bucket writes are stored. The Samachar bypass and the other limits above remain open. Full evidence is in `operational_integration_sprint/PHASE2_COMPLETION_REPORT.md` and `TESTING_PACKET.md`.
