import logging
import easyocr
import numpy as np
import ssl

# Bypass SSL verification to allow downloading EasyOCR models in restricted environments
ssl._create_default_https_context = ssl._create_unverified_context

from app.core.config import settings
from app.models.schemas import OCRResult, BoundingBox

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        # Initialized lazily on first call
        self.reader = None

    def initialize(self):
        if self.reader is not None:
            return
        try:
            logger.info("Initializing EasyOCR reader (cpu mode)...")
            # BUG FIX: gpu=True hard-crashes on Render (CPU-only). Use gpu=False so EasyOCR
            # runs on CPU and auto-upgrades to GPU if CUDA is available later.
            self.reader = easyocr.Reader(settings.OCR_LANGUAGES, gpu=False)
            logger.info("EasyOCR reader initialized successfully.")
        except Exception as exc:
            logger.exception("Failed to initialize EasyOCR reader: %s", exc)
            self.reader = None
            raise RuntimeError(f"OCR initialization failed: {exc}") from exc

    def extract_text(self, image: np.ndarray) -> list[OCRResult]:
        self.initialize()
        if self.reader is None:
            logger.warning("OCR reader is None — skipping OCR stage.")
            return []

        try:
            results = self.reader.readtext(image)
        except Exception as exc:
            logger.exception("EasyOCR readtext() raised an exception: %s", exc)
            return []

        ocr_results = []
        for (bbox, text, prob) in results:
            try:
                # bbox is a list of 4 points: [top-left, top-right, bottom-right, bottom-left]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
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
