# Vision Intelligence Runtime v1 Review Packet

## Objective Met
Delivered a working, indigenous Vision Intelligence Runtime ready for immediate consumption by Samachar and integration by SVACS without architectural changes. The runtime is modular, deterministic, replay-safe, and plug-and-play.

## Deliverables Status

- **Working Vision Runtime**: ✅ Built with FastAPI, Pydantic, OpenCV, EasyOCR, and YOLOv8.
- **OCR Integration**: ✅ EasyOCR implemented in `app/services/ocr_service.py`. Extracts text and bounds.
- **Vessel Classification Engine**: ✅ YOLOv8 inference scaffolded in `app/services/inference_service.py`. Maps generic COCO classes (e.g., 'boat') to maritime labels until a custom vessel model is swapped in.
- **REST API**: ✅ Exposed via `/api/v1/analyze` and `/api/v1/batch-analyze`.
- **Batch Inference**: ✅ Supported via `/api/v1/batch-analyze` array processing.
- **Replay Evidence**: ✅ Implemented in `app/services/replay_service.py`. Saves input image, complete response payload (excluding large base64 image data to save disk space), and execution metadata in a dedicated `replays/<uuid>/` folder per request.
- **Confidence Scoring**: ✅ Handled intrinsically by YOLOv8 and EasyOCR, included in output JSON schema.
- **Explainability Output**: ✅ Implemented in `app/services/explainability.py`. Renders bounding boxes and labels for OCR and classifications back onto the original image as visual evidence.
- **CPU/GPU Support**: ✅ EasyOCR and YOLOv8 are configured to attempt GPU usage natively, but will seamlessly fallback to CPU.
- **Structured Contracts**: ✅ Defined tightly using Pydantic in `app/models/schemas.py`.

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

## Notes for SVACS Integration (Nupur & Ankita)

The standard response contract (`VisionAnalysisResponse`) looks like this:
```json
{
  "replay_id": "uuid-v4-string",
  "detections": [
    {
      "label": "Vessel",
      "confidence": 0.89,
      "bounding_box": {"x_min": 0.0, "y_min": 0.0, "x_max": 100.0, "y_max": 100.0}
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

This contract is final and replay-safe. If downstream models become more granular (e.g. Tanker vs Patrol Boat), only the `"label"` string will change.

## Action Items
- Provide the custom trained Vessel weights (if any exist) so `app/core/config.py` can be updated to point to it instead of the generic `yolov8n.pt`.
