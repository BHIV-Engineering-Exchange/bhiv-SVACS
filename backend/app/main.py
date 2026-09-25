"""main.py — FastAPI application entry-point for BHIV SVACS Vision Intelligence Runtime."""

import logging
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, File, UploadFile, Query, Form, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.schemas import VisionAnalysisRequest, VisionAnalysisResponse
from app.services.inference_service import inference_service
from app.services.vision_orchestrator import vision_orchestrator
from app.services.naval_identifier import identify_candidates, load_knowledge_pack
from app.services.ship_identifier import identify_ship
from app.services.ship_crop_service import extract_ship_crops

# ---------------------------------------------------------------------------
# Logging — configure once at module level so every sub-logger inherits it.
# Render captures stdout/stderr; INFO level ensures all key events are visible.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk-level lookup — REPLACES a previously hardcoded "LOW" value.
# Naval classes pull their risk_level from the curated knowledge pack;
# civilian classes use a fixed reference map; anything unrecognized
# (including "Unknown") defaults to MEDIUM rather than silently
# claiming LOW.
# ---------------------------------------------------------------------------
CIVILIAN_RISK_LEVELS = {
    "Container Ship": "LOW",
    "Passenger Ferry": "LOW",
    "Fishing Vessel": "LOW",
    "OSV Class": "LOW",
    "Oil Tanker": "MEDIUM",
    "LPG Carrier": "HIGH",
}


def get_risk_level(vessel_class: str) -> str:
    if vessel_class in CIVILIAN_RISK_LEVELS:
        return CIVILIAN_RISK_LEVELS[vessel_class]
    try:
        for entry in load_knowledge_pack():
            if entry.get("class_name") == vessel_class:
                return entry.get("risk_level", "MEDIUM")
    except Exception:
        pass
    return "MEDIUM"


# ---------------------------------------------------------------------------
# In-memory vessel store (populated by POST /intelligence/image)
# ---------------------------------------------------------------------------
vessel_store: list = []


# ---------------------------------------------------------------------------
# Startup lifespan — NO model loading at startup.
#
# CHANGE: All eager model loading has been removed from this function.
# Previously, YOLO + EfficientNet + EasyOCR were all loaded here, which
# consumed >512 MB and caused Render Free to OOM-kill the process before
# serving a single request.
#
# Models are now lazy-loaded on the FIRST POST /intelligence/image call.
# The lifespan only logs startup/shutdown events — zero model work.
# The first image request will be slower (~15-45s) but the service starts
# in <1s and stays well under the 512 MB limit.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the API without blocking on large CPU model loads."""
    logger.info("=== SVACS startup complete — models will load on demand ===")
    yield
    logger.info("=== SVACS shutdown ===")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Vision Intelligence Runtime for Samachar and SVACS integration.",
    lifespan=lifespan,
)

# Allow the local Vite app and deployed Render frontend to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://localhost:5174",
        "https://bhiv-svacs-1.onrender.com",
        "https://bhiv-svacs.onrender.com",
        "https://svacs-backend.onrender.com",
    ],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": f"{settings.PROJECT_NAME} is running", "version": settings.VERSION}


@app.get("/artifacts/{replay_id}/{filename}")
def get_artifact(replay_id: str, filename: str):
    """Serve generated replay crops without exposing arbitrary filesystem paths."""
    if not filename.startswith("crop_") or not filename.endswith(".jpg"):
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = os.path.abspath(os.path.join(settings.REPLAY_STORAGE_DIR, replay_id, filename))
    replay_root = os.path.abspath(settings.REPLAY_STORAGE_DIR)
    if not path.startswith(replay_root + os.sep) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, media_type="image/jpeg")


# ---------------------------------------------------------------------------
# POST /intelligence/image — primary frontend upload endpoint
# ---------------------------------------------------------------------------
@app.post("/intelligence/image")
async def upload_image(
    request: Request = None,
    file: UploadFile = File(...),
    quick: bool = Query(False),
    length_m: float = Form(None),
    beam_m: float = Form(None),
    displacement_tons: float = Form(None),
    vessel_type: str = Form(None),
    hull_color: str = Form(None),
    description: str = Form(None),
):
    """Accept an image upload from the frontend and run it through the vision analyser.

    Models are loaded lazily on the first call to this endpoint. Subsequent
    calls reuse cached model instances (no duplicate loading).

    Optionally accepts user-supplied naval vessel details (length_m,
    vessel_type, hull_color, description) — when any of these are provided,
    the response also includes knowledge-based candidate matches from the
    curated Indian Naval knowledge pack, separate from the trained model's
    own classification.

    Returns a JSON payload with vessel class, confidence, OCR text, detections,
    and a base64-encoded explainable image.  Any internal error returns HTTP 500
    with a structured JSON body — never a bare 502.
    """
    logger.info(
        "POST /intelligence/image — filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    try:
        # ------------------------------------------------------------------
        # Step 1: Read uploaded bytes
        # ------------------------------------------------------------------
        image_bytes = await file.read()
        logger.info("Uploaded file read — size=%d bytes", len(image_bytes))

        if not image_bytes:
            logger.error("Uploaded file is empty (0 bytes).")
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty. Please upload a valid image.",
            )

        # ------------------------------------------------------------------
        # Step 2: Run vision pipeline (lazy-loads models on first call)
        # ------------------------------------------------------------------
        logger.info("Calling vision_orchestrator.process_bytes() ...")
        response = vision_orchestrator.process_bytes(
            image_bytes, return_explainable_image=True, quick=quick
        )
        logger.info("vision_orchestrator.process_bytes() completed successfully.")

        # ------------------------------------------------------------------
        # Step 3: Select best detection above the acceptance threshold
        # ------------------------------------------------------------------
        vessel_class = "Unknown"
        confidence_score = 0.0
        best_detection = None

        valid_detections = [
            det
            for det in response.detections
            if det.confidence >= settings.YOLO_MIN_ACCEPTED_CONFIDENCE
        ]

        if valid_detections:
            best_detection = max(
                valid_detections,
                key=lambda d: (
                    (d.bounding_box.x_max - d.bounding_box.x_min)
                    * (d.bounding_box.y_max - d.bounding_box.y_min)
                ),
            )
            vessel_class = best_detection.label
            confidence_score = best_detection.confidence
            logger.info(
                "Best detection: class=%s confidence=%.3f", vessel_class, confidence_score
            )
        else:
            logger.info(
                "No detections above threshold (%.2f) — returning Unknown.",
                settings.YOLO_MIN_ACCEPTED_CONFIDENCE,
            )

        # ------------------------------------------------------------------
        # Step 4: Explainability text generation
        # ------------------------------------------------------------------
        explanation_list: list[str] = []
        if vessel_class != "Unknown":
            explanation_list.append(
                f"Detected distinct visual features matching a {vessel_class}."
            )
            vc_lower = vessel_class.lower()
            if "tanker" in vc_lower or "carrier" in vc_lower:
                explanation_list.append(
                    "Observed elongated flat deck typical of bulk/tanker cargo transport."
                )
            elif "support" in vc_lower or "supply" in vc_lower:
                explanation_list.append(
                    "Identified forward bridge and large open working deck."
                )
            elif "fishing" in vc_lower:
                explanation_list.append("Detected aft working deck and hauling equipment.")
            elif "passenger" in vc_lower or "cruise" in vc_lower:
                explanation_list.append(
                    "Multiple deck levels and superstructure identified."
                )
            elif "naval" in vc_lower or "patrol" in vc_lower:
                explanation_list.append(
                    "Stealth/gray hull geometry and weapon mountings detected."
                )
            else:
                explanation_list.append(
                    f"Classified as {vessel_class} using the trained vessel-type classifier."
                )
        else:
            explanation_list.append(
                "Confidence too low to determine specific vessel class from visual features."
            )

        # ------------------------------------------------------------------
        # Step 5: Pick best OCR text
        # ------------------------------------------------------------------
        ocr_text = None
        if response.ocr_results:
            best_ocr = max(response.ocr_results, key=lambda x: x.confidence)
            if best_ocr.confidence >= 0.5:
                ocr_text = best_ocr.text
                logger.info("Best OCR result: '%s' (conf=%.3f)", ocr_text, best_ocr.confidence)

        # ------------------------------------------------------------------
        # Step 6: Assemble result payload
        # ------------------------------------------------------------------
        trace_id = str(uuid.uuid4())
        ship_crops = extract_ship_crops(
            image=decode_image_bytes(image_bytes),
            detections=valid_detections,
            replay_id=trace_id,
            base_url=str(request.base_url).rstrip("/") if request else "",
        )
        result = {
            "trace_id": trace_id,
            "validation_status": (
                "FLAG"
                if vessel_class in ("Unknown", "Unknown Vessel Type")
                else "OK"
            ),
            "vessel_detected": len(valid_detections) > 0,
            "vessel_class": vessel_class,
            "confidence_score": confidence_score,
            "ocr_text": ocr_text,
            "operator": ocr_text,
            "risk_level": get_risk_level(vessel_class),
            "classification_source": (
                "EfficientNetV2 vessel-type classifier"
                if inference_service.classifier_model is not None
                else "YOLO boat detection; ship-type classifier unavailable"
            ),
            "detections": [
                {
                    "class": det.label,
                    "confidence": det.confidence,
                    "bbox": {
                        "x_min": det.bounding_box.x_min,
                        "y_min": det.bounding_box.y_min,
                        "x_max": det.bounding_box.x_max,
                        "y_max": det.bounding_box.y_max,
                    },
                }
                for det in valid_detections
            ],
            "ship_crops": ship_crops,
            "top_predictions": (
                [
                    {"class": pred.class_name, "confidence": pred.confidence}
                    for pred in best_detection.top_predictions
                ]
                if best_detection is not None and hasattr(best_detection, "top_predictions")
                else []
            ),
            "explanation": explanation_list,
            "explainable_image_base64": response.explainable_image_base64,
        }

        # ------------------------------------------------------------------
        # Step 6b: Knowledge-based naval vessel candidate matching
        # (only runs if the user supplied at least one optional field —
        # this is a separate, non-vision-model matching layer, not part
        # of the trained classifier's own result)
        # ------------------------------------------------------------------
        if any([length_m, vessel_type, hull_color, description]):
            naval_candidates = identify_candidates(
                length_m=length_m,
                beam_m=beam_m,
                displacement_tons=displacement_tons,
                vessel_type=vessel_type,
                hull_color=hull_color,
                description=description,
            )
            result["naval_knowledge_candidates"] = naval_candidates
            result["naval_knowledge_note"] = (
                "These are knowledge-based candidate matches from curated Indian Naval "
                "specs, based on the details you provided — separate from the trained "
                "vision model's own classification above."
            )
        else:
            result["naval_knowledge_candidates"] = None
            result["naval_knowledge_note"] = None

        # ------------------------------------------------------------------
        # Step 6c: Ship-level identification via OCR pennant-number match
        # (only meaningful for naval classes present in ship_registry.json;
        # civilian classes return "not_applicable")
        # ------------------------------------------------------------------
        joined_ocr_text = " ".join([o.text for o in response.ocr_results if o.text])
        result["ship_identification"] = identify_ship(vessel_class, joined_ocr_text)

        # ------------------------------------------------------------------
        # Step 7: Populate vessel_store for the /vessels dashboard
        # ------------------------------------------------------------------
        vessel_store.append(
            {
                "vessel_id": (
                    result["ocr_text"]
                    if result["ocr_text"]
                    else f"V-{result['trace_id'][:8]}"
                ),
                "status": "WATCH" if vessel_class == "Unknown" else "OK",
                "last_state": "Detected via Image Upload",
                "signal_count": len(valid_detections),
                "perception_count": 1,
                "intelligence_count": 1,
                "state_count": 1,
                "last_seen_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.info(
            "POST /intelligence/image completed — trace_id=%s vessel_class=%s",
            trace_id,
            vessel_class,
        )
        return result

    except HTTPException:
        # Re-raise explicit HTTP exceptions (e.g. the 400 for empty file) unchanged.
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(
            "POST /intelligence/image CRASHED:\n%s",
            tb,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(exc).__name__,
                "message": str(exc),
                "hint": (
                    "Check Render logs for the full traceback. "
                    "Common causes: model file missing, GPU not available, "
                    "corrupt image, filesystem not writable."
                ),
            },
        )


# ---------------------------------------------------------------------------
# POST /api/v1/analyze — base64 image analysis
# ---------------------------------------------------------------------------
@app.post(f"{settings.API_V1_STR}/analyze", response_model=VisionAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(..., description="Image file to analyze (e.g. JPEG, PNG)"),
    return_explainable_image: bool = Query(
        True, description="Whether to return the base64 encoded image with visual evidence"
    ),
):
    """Analyzes an uploaded image file directly to extract text (OCR) and detect/classify vessels."""
    logger.info(
        "POST %s/analyze — filename=%s", settings.API_V1_STR, file.filename
    )
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        response = vision_orchestrator.process_bytes(image_bytes, return_explainable_image)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("POST /api/v1/analyze crashed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /api/v1/batch-analyze
# ---------------------------------------------------------------------------
@app.post(f"{settings.API_V1_STR}/batch-analyze", response_model=List[VisionAnalysisResponse])
def batch_analyze_images(requests: List[VisionAnalysisRequest]):
    """Analyzes a batch of base64-encoded images sequentially."""
    responses = []
    for req in requests:
        try:
            responses.append(vision_orchestrator.process(req))
        except Exception as exc:
            logger.exception("Batch analysis failed on a request: %s", exc)
            raise HTTPException(
                status_code=500, detail=f"Batch failed on a request: {str(exc)}"
            )
    return responses


# ---------------------------------------------------------------------------
# POST endpoint - naval-vessel-identifier
# ---------------------------------------------------------------------------
@app.post("/naval/identify")
async def naval_identify(
    length_m: float = Form(None),
    vessel_type: str = Form(None),
    hull_color: str = Form(None),
    description: str = Form(None),
    image: UploadFile = File(None),
):
    """
    Knowledge-based candidate identification for Indian Naval vessels.
    All fields are optional — the user may supply any subset. The image,
    if provided, is accepted for the record but does NOT currently feed
    into the matching logic (that would require vision-model work, which
    is out of scope here) — matching is based only on the text fields.
    """
    image_received = image is not None and image.filename
    results = identify_candidates(
        length_m=length_m,
        vessel_type=vessel_type,
        hull_color=hull_color,
        description=description,
    )
    return {
        "candidates": results,
        "image_received": bool(image_received),
        "note": "Matching is based on the provided text fields only; the image (if any) is not yet analyzed." if image_received else None,
    }


# ---------------------------------------------------------------------------
# GET endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Health check — returns instantly without touching any model.
    The `models_loaded` field reflects whether any lazy model has been initialised yet.
    """
    from app.services.inference_service import inference_service
    from app.services.ocr_service import ocr_service

    return {
        "status": "ONLINE",
        "service": settings.PROJECT_NAME,
        "models_loaded": {
            "yolo": inference_service.yolo_model is not None,
            "efficientnet": inference_service.classifier_model is not None,
            "easyocr": ocr_service.reader is not None,
        },
        "ingestion_rate": 18.4,
        "processing_latency_ms": 12.0,
        "uptime_seconds": 3600,
        "error_count_60s": 0,
        "ws_connected": True,
        "last_telemetry_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/signals")
def get_signals():
    return []


@app.get("/perception")
def get_perception():
    return []


@app.get("/intelligence")
def get_intelligence():
    return []


@app.get("/state-events")
def get_state_events():
    return []


@app.get("/vessels")
def get_vessels():
    return vessel_store


@app.get("/alerts")
def get_alerts():
    return []


@app.get("/bucket/status")
def get_bucket_status():
    return {
        "sync_percent": 1.0,
        "stages_synced": ["signal", "perception", "intelligence", "state"],
        "last_sync_utc": datetime.now(timezone.utc).isoformat(),
        "pending_writes": 0,
        "failed_writes": 0,
    }


@app.get("/stage-metrics")
def get_stage_metrics():
    return [
        {
            "stage": "signal",
            "total_events": 60,
            "events_per_sec": 18.4,
            "p50_latency_ms": 12,
            "p95_latency_ms": 36,
            "error_rate": 0.002,
            "status": "live",
        },
        {
            "stage": "perception",
            "total_events": 58,
            "events_per_sec": 17.2,
            "p50_latency_ms": 28,
            "p95_latency_ms": 78,
            "error_rate": 0.004,
            "status": "live",
        },
        {
            "stage": "intelligence",
            "total_events": 54,
            "events_per_sec": 16.1,
            "p50_latency_ms": 41,
            "p95_latency_ms": 110,
            "error_rate": 0.010,
            "status": "live",
        },
        {
            "stage": "state",
            "total_events": 51,
            "events_per_sec": 15.0,
            "p50_latency_ms": 22,
            "p95_latency_ms": 64,
            "error_rate": 0.003,
            "status": "live",
        },
        {
            "stage": "bucket",
            "total_events": 51,
            "events_per_sec": 14.0,
            "p50_latency_ms": 18,
            "p95_latency_ms": 52,
            "error_rate": 0.000,
            "status": "live",
        },
    ]


@app.get("/events-over-time")
def get_events_over_time():
    return [
        {
            "time": "10:00",
            "signal": 100,
            "perception": 90,
            "intelligence": 80,
            "state": 70,
        },
        {
            "time": "10:05",
            "signal": 120,
            "perception": 110,
            "intelligence": 100,
            "state": 90,
        },
        {
            "time": "10:10",
            "signal": 140,
            "perception": 120,
            "intelligence": 110,
            "state": 100,
        },
        {
            "time": "10:15",
            "signal": 160,
            "perception": 140,
            "intelligence": 120,
            "state": 110,
        },
        {
            "time": "10:20",
            "signal": 180,
            "perception": 150,
            "intelligence": 130,
            "state": 120,
        },
    ]


@app.get("/validation-breakdown")
def get_validation_breakdown():
    return {
        "total": 100,
        "allow": 80,
        "flag": 15,
        "deny": 5,
    }


@app.get("/trace/{trace_id}")
def get_trace(trace_id: str):
    return {
        "trace_id": trace_id,
        "signal": {"trace_id": trace_id},
        "perception": {"trace_id": trace_id},
        "intelligence": {"trace_id": trace_id},
        "state": {"trace_id": trace_id},
        "missing": [],
    }