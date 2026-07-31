import logging
import uuid
import os
import json
import cv2
import numpy as np

from app.core.config import settings
from app.models.schemas import VisionAnalysisResponse
from datetime import datetime

logger = logging.getLogger(__name__)


class ReplayService:
    def save_replay(self, image: np.ndarray, response: VisionAnalysisResponse) -> str:
        """Saves the exact inputs and outputs for deterministic replay capability.

        This method is intentionally non-fatal: any I/O error is logged as a warning
        so that a filesystem problem on Render never propagates back to the HTTP response.
        """
        replay_id = response.replay_id

        try:
            # BUG FIX: Use the configured (now /tmp-based) REPLAY_STORAGE_DIR so Render's
            # read-only app filesystem does not cause a PermissionError.
            replay_dir = os.path.join(settings.REPLAY_STORAGE_DIR, replay_id)
            os.makedirs(replay_dir, exist_ok=True)

            # Save input image
            img_path = os.path.join(replay_dir, "input.jpg")
            success = cv2.imwrite(img_path, image)
            if not success:
                logger.warning("cv2.imwrite failed for replay %s — image not saved.", replay_id)

            # Save output contract (without bulky base64 image)
            contract_data = response.model_dump()
            if "explainable_image_base64" in contract_data:
                contract_data["explainable_image_base64"] = None

            with open(os.path.join(replay_dir, "contract.json"), "w") as f:
                json.dump(contract_data, f, indent=4)

            # Save metadata
            metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "model_version": settings.VERSION,
                "yolo_model": settings.YOLO_MODEL_PATH,
            }
            with open(os.path.join(replay_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=4)

            logger.info("Replay saved: %s", replay_id)

        except Exception as exc:
            # BUG FIX: Replay I/O errors are non-fatal. Log a warning and continue.
            logger.warning("Replay save failed for %s (non-fatal): %s", replay_id, exc)

        return replay_id


replay_service = ReplayService()
