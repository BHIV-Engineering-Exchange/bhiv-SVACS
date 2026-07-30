import uuid
import os
import json
import cv2
import numpy as np
from app.core.config import settings
from app.models.schemas import VisionAnalysisResponse
from datetime import datetime

class ReplayService:
    def save_replay(self, image: np.ndarray, response: VisionAnalysisResponse) -> str:
        """Saves the exact inputs and outputs for deterministic replay capability."""
        # Use the generated replay_id from the response
        replay_id = response.replay_id
        
        # Create a directory for this specific replay
        replay_dir = os.path.join(settings.REPLAY_STORAGE_DIR, replay_id)
        os.makedirs(replay_dir, exist_ok=True)
        
        # Save input image
        cv2.imwrite(os.path.join(replay_dir, "input.jpg"), image)
        
        # Save output contract
        contract_data = response.model_dump()
        # Do not save the base64 image in the json to save space if it's there
        if "explainable_image_base64" in contract_data:
            contract_data["explainable_image_base64"] = None
            
        with open(os.path.join(replay_dir, "contract.json"), "w") as f:
            json.dump(contract_data, f, indent=4)
            
        # Save metadata
        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "model_version": settings.VERSION,
            "yolo_model": settings.YOLO_MODEL_PATH
        }
        with open(os.path.join(replay_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        return replay_id

replay_service = ReplayService()
