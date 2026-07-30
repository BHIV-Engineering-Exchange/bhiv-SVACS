import uuid
import numpy as np
from app.models.schemas import VisionAnalysisRequest, VisionAnalysisResponse
from app.services.preprocessing import decode_base64_image, preprocess_for_inference, encode_image_base64, decode_image_bytes
from app.services.ocr_service import ocr_service
from app.services.inference_service import inference_service
from app.services.explainability import draw_evidence
from app.services.replay_service import replay_service

class VisionOrchestrator:
    def process_image(self, raw_image: np.ndarray, return_explainable_image: bool) -> VisionAnalysisResponse:
        # 1. Image Ingestion & Preprocessing
        processed_image = preprocess_for_inference(raw_image)
        
        # 2. OCR Extraction
        ocr_results = ocr_service.extract_text(processed_image)
        
        # 3. Detection & Classification
        detections = inference_service.detect(processed_image)
        
        # 4. Explainable Output Generation
        explainable_base64 = None
        if return_explainable_image:
            explained_image = draw_evidence(raw_image, detections, ocr_results)
            explainable_base64 = encode_image_base64(explained_image)
            
        # 5. Build Response
        replay_id = str(uuid.uuid4())
        response = VisionAnalysisResponse(
            replay_id=replay_id,
            detections=detections,
            ocr_results=ocr_results,
            explainable_image_base64=explainable_base64
        )
        
        # 6. Replay Artifact Generation
        replay_service.save_replay(raw_image, response)
        
        return response

    def process(self, request: VisionAnalysisRequest) -> VisionAnalysisResponse:
        raw_image = decode_base64_image(request.image_base64)
        return self.process_image(raw_image, request.return_explainable_image)

    def process_bytes(self, image_bytes: bytes, return_explainable_image: bool) -> VisionAnalysisResponse:
        raw_image = decode_image_bytes(image_bytes)
        return self.process_image(raw_image, return_explainable_image)

vision_orchestrator = VisionOrchestrator()

