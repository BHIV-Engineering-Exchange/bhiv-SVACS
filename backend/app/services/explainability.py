import cv2
import numpy as np
from app.models.schemas import DetectionResult, OCRResult
from typing import List

def draw_evidence(image: np.ndarray, detections: List[DetectionResult], ocr_results: List[OCRResult]) -> np.ndarray:
    """Draws bounding boxes and labels on the image for explainability."""
    output_image = image.copy()
    
    # Draw detections (red boxes)
    for det in detections:
        bbox = det.bounding_box
        cv2.rectangle(
            output_image,
            (int(bbox.x_min), int(bbox.y_min)),
            (int(bbox.x_max), int(bbox.y_max)),
            (0, 0, 255),
            2
        )
        label_text = f"{det.label} {det.confidence:.2f}"
        cv2.putText(
            output_image,
            label_text,
            (int(bbox.x_min), int(bbox.y_min) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2
        )

    # Draw OCR results (green boxes)
    for ocr in ocr_results:
        bbox = ocr.bounding_box
        cv2.rectangle(
            output_image,
            (int(bbox.x_min), int(bbox.y_min)),
            (int(bbox.x_max), int(bbox.y_max)),
            (0, 255, 0),
            2
        )
        label_text = f"OCR: {ocr.text}"
        cv2.putText(
            output_image,
            label_text,
            (int(bbox.x_min), int(bbox.y_max) + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2
        )
        
    return output_image
