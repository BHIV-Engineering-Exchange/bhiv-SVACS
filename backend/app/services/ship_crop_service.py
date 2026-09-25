"""Extract and persist one image crop for each accepted ship detection."""

import os
from typing import Any

import cv2
import numpy as np

from app.core.config import settings


def extract_ship_crops(
    image: np.ndarray,
    detections: list[Any],
    replay_id: str,
    base_url: str,
    padding_ratio: float = 0.05,
) -> list[dict[str, Any]]:
    """Save valid detection crops and return their API metadata.

    Detection IDs are assigned in response order. Invalid or degenerate boxes
    remain represented with a null URL so one bad detection cannot discard the
    rest of the response.
    """
    if image is None or image.size == 0:
        return []

    height, width = image.shape[:2]
    crop_dir = os.path.join(settings.REPLAY_STORAGE_DIR, replay_id)
    os.makedirs(crop_dir, exist_ok=True)
    crops: list[dict[str, Any]] = []

    for index, detection in enumerate(detections, start=1):
        box = detection.bounding_box
        bounding_box = {
            "x_min": box.x_min,
            "y_min": box.y_min,
            "x_max": box.x_max,
            "y_max": box.y_max,
        }
        item: dict[str, Any] = {
            "detection_id": f"detection-{index}",
            "label": detection.label,
            "confidence": detection.confidence,
            "bounding_box": bounding_box,
            "crop_image_url": None,
        }

        try:
            x_min, y_min, x_max, y_max = map(float, bounding_box.values())
            if not all(np.isfinite(value) for value in (x_min, y_min, x_max, y_max)):
                crops.append(item)
                continue

            box_width = x_max - x_min
            box_height = y_max - y_min
            if box_width <= 0 or box_height <= 0:
                crops.append(item)
                continue

            pad_x = box_width * padding_ratio
            pad_y = box_height * padding_ratio
            left = max(0, int(np.floor(x_min - pad_x)))
            top = max(0, int(np.floor(y_min - pad_y)))
            right = min(width, int(np.ceil(x_max + pad_x)))
            bottom = min(height, int(np.ceil(y_max + pad_y)))
            if left >= right or top >= bottom:
                crops.append(item)
                continue

            crop = image[top:bottom, left:right]
            filename = f"crop_{index:03d}.jpg"
            path = os.path.join(crop_dir, filename)
            if not cv2.imwrite(path, crop):
                crops.append(item)
                continue
            item["crop_image_url"] = f"{base_url.rstrip('/')}/artifacts/{replay_id}/{filename}"
        except (TypeError, ValueError, OverflowError, cv2.error):
            pass

        crops.append(item)

    return crops