"""vision_orchestrator.py — Orchestrates the full vision pipeline.

Every stage is wrapped in its own try/except so a single step failure
(OCR, YOLO, classification, explainability, replay) produces a clear log
entry and gracefully degrades rather than crashing the HTTP response.
"""
import logging
import traceback
import uuid
import numpy as np

from app.models.schemas import VisionAnalysisRequest, VisionAnalysisResponse
from app.services.preprocessing import (
    decode_base64_image,
    preprocess_for_inference,
    encode_image_base64,
    decode_image_bytes,
)
from app.services.ocr_service import ocr_service
from app.services.inference_service import inference_service
from app.services.explainability import draw_evidence
from app.services.replay_service import replay_service

logger = logging.getLogger(__name__)


class VisionOrchestrator:
    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def process_image(
        self, raw_image: np.ndarray, return_explainable_image: bool
    ) -> VisionAnalysisResponse:
        """Run the full pipeline on a decoded BGR numpy image.

        Each stage is isolated in its own try/except:
          1. Preprocessing
          2. OCR extraction
          3. YOLO + EfficientNet detection/classification
          4. Explainability overlay
          5. Replay save
        """
        replay_id = str(uuid.uuid4())

        # Validate the image before doing anything else
        if raw_image is None or raw_image.size == 0:
            logger.error("process_image() received an empty/None image (replay_id=%s)", replay_id)
            raise ValueError(
                "Image could not be decoded — the uploaded file may be empty or corrupt."
            )

        logger.info(
            "process_image() start — shape=%s dtype=%s replay_id=%s",
            raw_image.shape,
            raw_image.dtype,
            replay_id,
        )

        # ----------------------------------------------------------------
        # Stage 1: Preprocessing
        # ----------------------------------------------------------------
        try:
            processed_image = preprocess_for_inference(raw_image)
            logger.info("Stage 1 (preprocessing) OK — output shape: %s", processed_image.shape)
        except Exception as exc:
            logger.exception("Stage 1 (preprocessing) FAILED: %s", exc)
            raise RuntimeError(f"Preprocessing failed: {exc}") from exc

        # ----------------------------------------------------------------
        # Stage 2: OCR extraction (non-fatal — returns [] on failure)
        # ----------------------------------------------------------------
        ocr_results = []
        try:
            ocr_results = ocr_service.extract_text(processed_image)
            logger.info("Stage 2 (OCR) OK — %d results", len(ocr_results))
        except Exception as exc:
            logger.exception("Stage 2 (OCR) FAILED (non-fatal, continuing): %s", exc)
            # OCR failure is non-fatal; the pipeline continues with no text results.

        # ----------------------------------------------------------------
        # Stage 3: YOLO detection + EfficientNet classification
        # ----------------------------------------------------------------
        try:
            detections = inference_service.detect(processed_image)
            logger.info("Stage 3 (detection) OK — %d detection(s)", len(detections))
        except Exception as exc:
            logger.exception("Stage 3 (detection) FAILED: %s", exc)
            raise RuntimeError(f"Vessel detection failed: {exc}") from exc

        # ----------------------------------------------------------------
        # Stage 4: Explainability overlay (non-fatal)
        # ----------------------------------------------------------------
        explainable_base64 = None
        if return_explainable_image:
            try:
                explained_image = draw_evidence(raw_image, detections, ocr_results)
                explainable_base64 = encode_image_base64(explained_image)
                logger.info("Stage 4 (explainability) OK — base64 length: %d", len(explainable_base64))
            except Exception as exc:
                logger.exception("Stage 4 (explainability) FAILED (non-fatal): %s", exc)
                # Return the image without an overlay rather than crashing.

        # ----------------------------------------------------------------
        # Stage 5: Build response
        # ----------------------------------------------------------------
        response = VisionAnalysisResponse(
            replay_id=replay_id,
            detections=detections,
            ocr_results=ocr_results,
            explainable_image_base64=explainable_base64,
        )

        # ----------------------------------------------------------------
        # Stage 6: Replay save (non-fatal)
        # ----------------------------------------------------------------
        try:
            replay_service.save_replay(raw_image, response)
            logger.info("Stage 6 (replay save) OK — replay_id=%s", replay_id)
        except Exception as exc:
            logger.warning("Stage 6 (replay save) FAILED (non-fatal): %s", exc)

        logger.info("process_image() completed successfully — replay_id=%s", replay_id)
        return response

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, request: VisionAnalysisRequest) -> VisionAnalysisResponse:
        """Accepts a base64-encoded image from the VisionAnalysisRequest schema."""
        logger.info("process() called via base64 path")
        try:
            raw_image = decode_base64_image(request.image_base64)
        except Exception as exc:
            logger.exception("Base64 image decode failed: %s", exc)
            raise ValueError(f"Invalid base64 image: {exc}") from exc
        return self.process_image(raw_image, request.return_explainable_image)

    def process_bytes(
        self, image_bytes: bytes, return_explainable_image: bool
    ) -> VisionAnalysisResponse:
        """Accepts raw image bytes (e.g. from an UploadFile.read())."""
        logger.info("process_bytes() called — received %d bytes", len(image_bytes))

        if not image_bytes:
            logger.error("process_bytes() received zero-length bytes.")
            raise ValueError("Uploaded file is empty — no image data received.")

        try:
            raw_image = decode_image_bytes(image_bytes)
        except Exception as exc:
            logger.exception("OpenCV image decode failed: %s", exc)
            raise ValueError(
                f"OpenCV could not decode the uploaded image. "
                f"Ensure the file is a valid JPEG/PNG. Detail: {exc}"
            ) from exc

        if raw_image is None or raw_image.size == 0:
            logger.error("decode_image_bytes() returned an empty image.")
            raise ValueError(
                "OpenCV decoded an empty image. "
                "The file may be corrupt or an unsupported format."
            )

        logger.info("Image decoded OK — shape: %s", raw_image.shape)
        return self.process_image(raw_image, return_explainable_image)


vision_orchestrator = VisionOrchestrator()
