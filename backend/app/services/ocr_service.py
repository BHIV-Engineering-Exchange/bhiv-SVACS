"""ocr_service.py — Lazy-loading EasyOCR service with pre-bundled models.

CHANGES vs original:
  1. `import easyocr` moved inside initialize() — the EasyOCR package itself
     triggers heavy imports (torch, torchvision backends) when imported at
     module level. Deferring this to the first call keeps startup RAM minimal.

  2. Removed the global `ssl._create_unverified_context` hack — it was a
     security risk and was only needed because EasyOCR tried to download models
     at runtime. We now pre-bundle models via the build step instead.

  3. `model_storage_directory` is set to the `ocr_models/` directory committed
     to the repo (populated by `scripts/download_ocr_models.py` at build time).
     EasyOCR will find the files there and never hit the network.

  4. `download_enabled=False` — hard-fails with a clear error if a model file
     is missing, rather than silently downloading and triggering an OOM.

  5. Added a threading.Lock so concurrent first requests don't each initialize
     their own EasyOCR Reader (each Reader = ~150 MB of RAM).
"""

import logging
import os
import threading
from typing import Optional

import numpy as np

from app.core.config import settings
from app.models.schemas import OCRResult, BoundingBox

logger = logging.getLogger(__name__)

# Path where OCR model weights live — populated at build time by
# scripts/download_ocr_models.py and committed to the repo.
_OCR_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ocr_models")
)

# One global lock prevents duplicate Reader construction under concurrent requests.
_init_lock = threading.Lock()


class OCRService:
    def __init__(self):
        # Initialised lazily on first call to extract_text()
        self.reader = None
        self._initialized: bool = False

    def initialize(self):
        """Construct the EasyOCR Reader if not already done.

        Thread-safe: _init_lock prevents duplicate initialisation under
        concurrent requests. Idempotent: no-op if already initialised.
        """
        # Fast path
        if self._initialized:
            return

        with _init_lock:
            # Double-checked locking
            if self._initialized:
                return

            # Deferred import — easyocr pulls in torch/torchvision on import,
            # which costs ~50 MB RSS even before any Reader is constructed.
            import easyocr

            try:
                logger.info("Initializing EasyOCR reader (cpu mode) ...")

                # Determine whether the pre-bundled model directory exists.
                # If it does, point EasyOCR at it and disable downloads.
                # If it doesn't (e.g., local dev without running the download
                # script), fall back to the default EasyOCR behaviour with
                # downloads enabled so developers can still work offline.
                if os.path.isdir(_OCR_MODEL_DIR) and os.listdir(_OCR_MODEL_DIR):
                    logger.info(
                        "Using pre-bundled OCR models from: %s", _OCR_MODEL_DIR
                    )
                    self.reader = easyocr.Reader(
                        settings.OCR_LANGUAGES,
                        gpu=False,
                        model_storage_directory=_OCR_MODEL_DIR,
                        download_enabled=False,  # Hard-fail if model files are missing
                    )
                else:
                    # Fallback for local dev / first-time setup without pre-bundled models
                    logger.warning(
                        "Pre-bundled OCR model directory '%s' is empty or missing. "
                        "Falling back to EasyOCR default download behaviour. "
                        "Run scripts/download_ocr_models.py to pre-bundle models.",
                        _OCR_MODEL_DIR,
                    )
                    self.reader = easyocr.Reader(
                        settings.OCR_LANGUAGES,
                        gpu=False,
                        download_enabled=True,
                    )

                self._initialized = True
                logger.info("EasyOCR reader initialized successfully.")

            except Exception as exc:
                logger.exception("Failed to initialize EasyOCR reader: %s", exc)
                self.reader = None
                raise RuntimeError(f"OCR initialization failed: {exc}") from exc

    def extract_text(self, image: np.ndarray) -> list[OCRResult]:
        """Extract text from a BGR numpy image.

        Calls initialize() on the first invocation (lazy load). Returns an
        empty list if the reader is unavailable — OCR failure is non-fatal.
        """
        if not settings.OCR_ENABLED:
            logger.info("OCR stage disabled by OCR_ENABLED=false.")
            return []

        try:
            self.initialize()
        except Exception as exc:
            logger.warning(
                "OCR initialization failed — skipping OCR stage: %s", exc
            )
            return []

        if self.reader is None:
            logger.warning("OCR reader is None — skipping OCR stage.")
            return []

        # Scale image down for OCR if larger than 1000px on longest side to save RAM and CPU time
        h, w = image.shape[:2]
        max_dim = 1000
        scale = 1.0
        ocr_input = image
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w, new_h = int(w * scale), int(h * scale)
            import cv2
            ocr_input = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        try:
            results = self.reader.readtext(ocr_input)
        except Exception as exc:
            logger.exception("EasyOCR readtext() raised an exception: %s", exc)
            return []

        ocr_results = []
        for (bbox, text, prob) in results:
            try:
                # Rescale bounding box coordinates back to original image dimensions
                x_coords = [p[0] / scale for p in bbox]
                y_coords = [p[1] / scale for p in bbox]
                bounding_box = BoundingBox(
                    x_min=float(min(x_coords)),
                    y_min=float(min(y_coords)),
                    x_max=float(max(x_coords)),
                    y_max=float(max(y_coords)),
                )
                ocr_results.append(
                    OCRResult(text=text, confidence=float(prob), bounding_box=bounding_box)
                )
            except Exception as exc:
                logger.warning("Skipping malformed OCR result: %s", exc)

        logger.info("OCR extracted %d text regions.", len(ocr_results))
        return ocr_results


ocr_service = OCRService()
