from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

class TopPrediction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    class_name: str = Field(..., alias="class")
    confidence: float

class DetectionResult(BaseModel):
    label: str
    confidence: float
    bounding_box: BoundingBox
    top_predictions: List[TopPrediction] = []

class OCRResult(BaseModel):
    text: str
    confidence: float
    bounding_box: BoundingBox

class VisionAnalysisResponse(BaseModel):
    replay_id: str
    detections: List[DetectionResult]
    ocr_results: List[OCRResult]
    explainable_image_base64: Optional[str] = Field(None, description="Base64 encoded image with bounding boxes drawn")

class VisionAnalysisRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image to analyze")
    return_explainable_image: bool = Field(True, description="Whether to return the base64 encoded image with visual evidence")

class DetectionDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    class_name: str = Field(..., alias="class")
    confidence: float
    bbox: BoundingBox

class UploadImageResponse(BaseModel):
    trace_id: str
    validation_status: str
    vessel_detected: bool
    vessel_class: str
    confidence_score: float
    ocr_text: Optional[str] = None
    operator: Optional[str] = None
    risk_level: str
    classification_source: str
    detections: List[DetectionDetail]
    top_predictions: List[TopPrediction] = []
    explanation: List[str]
    explainable_image_base64: Optional[str] = None
