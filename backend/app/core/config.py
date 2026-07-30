import os
from pydantic_settings import BaseSettings

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_YOLO_MODEL_PATH = os.path.join(BASE_DIR, "vessel_front_model.pt")

class Settings(BaseSettings):
    PROJECT_NAME: str = "BHIV Vision Intelligence Runtime"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Model config
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", DEFAULT_YOLO_MODEL_PATH)
    YOLO_IMAGE_SIZE: int = int(os.getenv("YOLO_IMAGE_SIZE", "640"))
    YOLO_CONFIDENCE_THRESHOLD: float = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.35"))
    YOLO_FALLBACK_CONFIDENCE_THRESHOLD: float = float(os.getenv("YOLO_FALLBACK_CONFIDENCE_THRESHOLD", "0.25"))
    YOLO_USE_FALLBACK: bool = str(os.getenv("YOLO_USE_FALLBACK", "true")).lower() in ("1", "true", "yes")
    YOLO_IOU_THRESHOLD: float = float(os.getenv("YOLO_IOU_THRESHOLD", "0.45"))
    YOLO_MAX_DETECTIONS: int = int(os.getenv("YOLO_MAX_DETECTIONS", "100"))
    YOLO_MIN_ACCEPTED_CONFIDENCE: float = float(os.getenv("YOLO_MIN_ACCEPTED_CONFIDENCE", "0.25"))
    # OCR config
    OCR_LANGUAGES: list[str] = ["en"]
    
    # Replay storage
    REPLAY_STORAGE_DIR: str = os.getenv("REPLAY_STORAGE_DIR", "replays")
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure replay directory exists
os.makedirs(settings.REPLAY_STORAGE_DIR, exist_ok=True)
