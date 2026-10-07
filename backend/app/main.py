"""main.py — FastAPI application entry-point for BHIV SVACS Vision Intelligence Runtime."""

import logging
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, File, UploadFile, Query, Form, Request, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.metrics import MetricsMiddleware, install_stage_logging, metrics
from app.core.security import auth_enabled, require_api_key
from app.models.schemas import VisionAnalysisRequest, VisionAnalysisResponse
from app.services.inference_service import inference_service
from app.services.vision_orchestrator import vision_orchestrator
from app.services.naval_identifier import identify_candidates, load_knowledge_pack
from app.services.ship_identifier import identify_ship, check_pennant_type_consistency
from app.services.ship_crop_service import extract_ship_crops
from app.services.preprocessing import decode_image_bytes

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
install_stage_logging()  # stage timings for /stage-metrics

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


def ocr_text_for_detection(ocr_results, detection_box, pad_ratio=0.15):
    """Returns only the OCR text whose bounding box center falls inside
    the given detection's own box (with a small padding tolerance),
    instead of every OCR reading in the whole image. This keeps a
    pennant number on one ship from being applied to a different ship
    when more than one vessel appears in the same photo."""
    x_min, y_min = detection_box.x_min, detection_box.y_min
    x_max, y_max = detection_box.x_max, detection_box.y_max
    pad_x = (x_max - x_min) * pad_ratio
    pad_y = (y_max - y_min) * pad_ratio
    ex_min, ex_max = x_min - pad_x, x_max + pad_x
    ey_min, ey_max = y_min - pad_y, y_max + pad_y

    matched = []
    for ocr in ocr_results:
        if not ocr.text:
            continue
        b = ocr.bounding_box
        cx = (b.x_min + b.x_max) / 2
        cy = (b.y_min + b.y_max) / 2
        if ex_min <= cx <= ex_max and ey_min <= cy <= ey_max:
            matched.append(ocr.text)
    return " ".join(matched)

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
    if auth_enabled():
        logger.info("API key authentication is ENABLED for POST endpoints.")
    else:
        logger.warning(
            "SVACS_API_KEY is not set: POST endpoints are OPEN to anyone who "
            "can reach this server. Set SVACS_API_KEY to enable authentication."
        )
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

# Count and time every request. Added after CORS so it is outermost and
# also sees preflights and authentication errors.
app.add_middleware(MetricsMiddleware)


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
@app.post("/intelligence/image", dependencies=[Depends(require_api_key)])
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
        # Step 6c/6d: per-detection ship identification and pennant/type
        # consistency check. Each detected ship gets its own OCR text,
        # limited to OCR boxes whose center falls inside that specific
        # detection's own bounding box, rather than every ship in the
        # image being checked against the same pooled OCR text. Results
        # are attached directly onto the matching ship_crops entry, so
        # multiple ships in one photo each get their own name, pennant
        # match, and misclassification warning. The top-level
        # ship_identification and pennant_type_check fields mirror
        # whichever detection was chosen as the overall "best" one, so
        # the summary section and that ship's own thumbnail never
        # disagree.
        # ------------------------------------------------------------------
        best_index = None
        if best_detection is not None:
            best_index = next(
                (i for i, d in enumerate(valid_detections) if d is best_detection), None
            )

        for i, det in enumerate(valid_detections):
            det_ocr_text = ocr_text_for_detection(response.ocr_results, det.bounding_box)
            det_ship_id = identify_ship(det.label, det_ocr_text)
            det_pennant_check = check_pennant_type_consistency(det.label, det_ocr_text)

            if i < len(ship_crops):
                ship_crops[i]["ship_identification"] = det_ship_id
                ship_crops[i]["pennant_type_check"] = det_pennant_check

            if i == best_index:
                result["ship_identification"] = det_ship_id
                result["pennant_type_check"] = det_pennant_check
                if det_pennant_check.get("checked") and not det_pennant_check.get("consistent"):
                    explanation_list.append(
                        f"Warning: OCR read pennant {det_pennant_check['pennant']}, which denotes a "
                        f"{det_pennant_check['ocr_implied_type']}, but the model predicted "
                        f"{vessel_class} ({det_pennant_check['predicted_class_type']}). "
                        "The class prediction may be wrong."
                    )
                    result["validation_status"] = "FLAG"

        if best_index is None:
            result["ship_identification"] = {"matched": False, "roster": [], "method": "not_applicable"}
            result["pennant_type_check"] = {"checked": False, "reason": "not_a_naval_class"}

        # ------------------------------------------------------------------
        # Step 7: Populate vessel_store for the /vessels dashboard
        # ------------------------------------------------------------------
        # Count this result in /validation-breakdown
        metrics.record_validation(result["validation_status"])
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
@app.post(f"{settings.API_V1_STR}/analyze", response_model=VisionAnalysisResponse, dependencies=[Depends(require_api_key)])
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
@app.post(f"{settings.API_V1_STR}/batch-analyze", response_model=List[VisionAnalysisResponse], dependencies=[Depends(require_api_key)])
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
@app.post("/naval/identify", dependencies=[Depends(require_api_key)])
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
    """Health check: returns instantly and never touches a model.

    Every number is computed from live traffic (app/core/metrics.py).
    ws_connected is False because this backend serves no WebSocket.
    """
    from app.core.security import auth_enabled
    from app.services.inference_service import inference_service
    from app.services.ocr_service import ocr_service

    snapshot = metrics.health_snapshot()
    return {
        "status": snapshot["status"],
        "service": settings.PROJECT_NAME,
        "auth_enabled": auth_enabled(),
        "models_loaded": {
            "yolo": inference_service.yolo_model is not None,
            "efficientnet": inference_service.classifier_model is not None,
            "easyocr": ocr_service.reader is not None,
        },
        "ingestion_rate": snapshot["ingestion_rate"],
        "processing_latency_ms": snapshot["processing_latency_ms"],
        "latency_samples": snapshot["latency_samples"],
        "uptime_seconds": snapshot["uptime_seconds"],
        "error_count_60s": snapshot["error_count_60s"],
        "ws_connected": False,
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
    """Bucket write outcomes since the server started."""
    return metrics.bucket_status()


@app.get("/metrics")
def get_metrics():
    """Full live metrics: per-route latency, per-stage timings, requests per
    minute over the last hour, Bucket and validation counts. Like the other
    GET endpoints it is not protected by the API key."""
    return metrics.summary()


@app.get("/stage-metrics")
def get_stage_metrics():
    """Timings of the image pipeline stages, measured from live traffic."""
    return metrics.stage_metrics()


@app.get("/events-over-time")
def get_events_over_time():
    """The dashboard chart plots the acoustic pipeline's stages (signal,
    perception, intelligence, state). This backend does not produce those
    events, so there is nothing real to report and an empty list is returned
    instead of invented numbers. Real request counts per minute are in
    /metrics."""
    return []


@app.get("/validation-breakdown")
def get_validation_breakdown():
    """Outcomes (allow / flag / deny) of the images analysed since start."""
    return metrics.validation_breakdown()


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