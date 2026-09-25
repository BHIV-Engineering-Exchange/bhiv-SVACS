import cv2
import numpy as np

from app.models.schemas import BoundingBox, DetectionResult
from app.services import ship_crop_service


def make_detection(label: str, confidence: float, box: tuple[float, float, float, float]):
    return DetectionResult(
        label=label,
        confidence=confidence,
        bounding_box=BoundingBox(
            x_min=box[0], y_min=box[1], x_max=box[2], y_max=box[3]
        ),
    )


def test_extract_ship_crops_with_zero_detections(tmp_path, monkeypatch):
    monkeypatch.setattr(ship_crop_service.settings, "REPLAY_STORAGE_DIR", str(tmp_path))

    crops = ship_crop_service.extract_ship_crops(
        np.zeros((100, 100, 3), dtype=np.uint8), [], "trace-0", "http://localhost:8000"
    )

    assert crops == []


def test_extract_ship_crops_with_one_detection(tmp_path, monkeypatch):
    monkeypatch.setattr(ship_crop_service.settings, "REPLAY_STORAGE_DIR", str(tmp_path))
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    detection = make_detection("Patrol Vessel", 0.91, (20, 25, 60, 75))

    crops = ship_crop_service.extract_ship_crops(
        image, [detection], "trace-1", "http://localhost:8000"
    )

    assert len(crops) == 1
    assert crops[0]["detection_id"] == "detection-1"
    assert crops[0]["label"] == "Patrol Vessel"
    assert crops[0]["crop_image_url"].endswith("/artifacts/trace-1/crop_001.jpg")
    assert cv2.imread(str(tmp_path / "trace-1" / "crop_001.jpg")).shape[:2] == (56, 44)


def test_extract_ship_crops_with_three_detections(tmp_path, monkeypatch):
    monkeypatch.setattr(ship_crop_service.settings, "REPLAY_STORAGE_DIR", str(tmp_path))
    image = np.zeros((120, 180, 3), dtype=np.uint8)
    detections = [
        make_detection("Ship A", 0.80, (0, 0, 40, 40)),
        make_detection("Ship B", 0.85, (60, 20, 100, 70)),
        make_detection("Ship C", 0.90, (130, 80, 180, 120)),
    ]

    crops = ship_crop_service.extract_ship_crops(
        image, detections, "trace-3", "http://localhost:8000"
    )

    assert len(crops) == 3
    assert [crop["detection_id"] for crop in crops] == [
        "detection-1",
        "detection-2",
        "detection-3",
    ]
    assert len(list((tmp_path / "trace-3").glob("crop_*.jpg"))) == 3


def test_extract_ship_crops_ignores_invalid_box_without_crashing(tmp_path, monkeypatch):
    monkeypatch.setattr(ship_crop_service.settings, "REPLAY_STORAGE_DIR", str(tmp_path))
    detection = make_detection("Invalid", 0.75, (80, 80, 20, 20))

    crops = ship_crop_service.extract_ship_crops(
        np.zeros((100, 100, 3), dtype=np.uint8),
        [detection],
        "trace-invalid",
        "http://localhost:8000",
    )

    assert crops == [
        {
            "detection_id": "detection-1",
            "label": "Invalid",
            "confidence": 0.75,
            "bounding_box": {"x_min": 80.0, "y_min": 80.0, "x_max": 20.0, "y_max": 20.0},
            "crop_image_url": None,
        }
    ]