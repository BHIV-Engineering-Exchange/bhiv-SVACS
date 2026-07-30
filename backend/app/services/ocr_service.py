import easyocr
import numpy as np
import ssl
# Bypass SSL verification to allow downloading EasyOCR models in restricted/Windows environments
ssl._create_default_https_context = ssl._create_unverified_context

from app.core.config import settings
from app.models.schemas import OCRResult, BoundingBox

class OCRService:
    def __init__(self):
        # Initialize reader lazily or on startup
        self.reader = None

    def initialize(self):
        if self.reader is None:
            self.reader = easyocr.Reader(settings.OCR_LANGUAGES, gpu=True) # Will fallback to CPU if no GPU

    def extract_text(self, image: np.ndarray) -> list[OCRResult]:
        self.initialize()
        results = self.reader.readtext(image)
        ocr_results = []
        for (bbox, text, prob) in results:
            # bbox is a list of 4 points: [top-left, top-right, bottom-right, bottom-left]
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            bounding_box = BoundingBox(
                x_min=float(min(x_coords)),
                y_min=float(min(y_coords)),
                x_max=float(max(x_coords)),
                y_max=float(max(y_coords))
            )
            ocr_results.append(OCRResult(
                text=text,
                confidence=float(prob),
                bounding_box=bounding_box
            ))
        return ocr_results

ocr_service = OCRService()
