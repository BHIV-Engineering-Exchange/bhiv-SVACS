import os
import torch
from typing import Optional
# Patch torch.load to bypass weights_only=True default in PyTorch 2.6
_original_torch_load = torch.load
def _custom_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _custom_torch_load

from ultralytics import YOLO
import numpy as np
from app.core.config import settings
from app.models.schemas import DetectionResult, BoundingBox, TopPrediction
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import torch.nn.functional as F

class InferenceService:
    def __init__(self):
        self.yolo_model = None
        self.classifier_model = None
        self.classes = [
            'Chemical Tanker', 'Container Ship', 'Cruise Ship', 
            'Fishing Trawler', 'Fishing Vessel', 'LPG Carrier', 
            'Oil Tanker', 'Passenger Ferry'
        ]
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def classify_full_image(self, image: np.ndarray) -> tuple[str, float, list[TopPrediction]]:
        """Use the EfficientNet classifier on the entire image as a fallback."""
        import cv2
        self.initialize()

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(image_rgb)
        device = next(self.classifier_model.parameters()).device
        input_tensor = self.transform(pil_img).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = self.classifier_model(input_tensor)
            probabilities = F.softmax(outputs, dim=1)[0]
            top3_prob, top3_catid = torch.topk(probabilities, 3)

        top_predictions = []
        for idx in range(len(top3_prob)):
            score = float(top3_prob[idx].item())
            label = self.classes[int(top3_catid[idx].item())]
            top_predictions.append(TopPrediction(**{"class": label, "confidence": round(score * 100, 2)}))

        return top_predictions[0].class_name, top_predictions[0].confidence / 100.0, top_predictions

    def refine_detection_label(self, label: str, top_preds: list[TopPrediction], bbox: BoundingBox) -> tuple[str, float, list[TopPrediction]]:
        """Apply shape and probability-based overrides for common ship-type confusion."""
        if not top_preds:
            return label, 0.0, top_preds

        aspect_ratio = (bbox.x_max - bbox.x_min) / max(1.0, bbox.y_max - bbox.y_min)

        def find_pred(name: str) -> Optional[TopPrediction]:
            return next((p for p in top_preds if p.class_name == name), None)

        container = find_pred("Container Ship")
        cruise = find_pred("Cruise Ship")
        ferry = find_pred("Passenger Ferry")
        fishing = find_pred("Fishing Vessel")
        oil = find_pred("Oil Tanker")

        # Cruise / Ferry vs Container confusion
        if label == "Container Ship":
            if cruise and cruise.confidence >= 12.0 and cruise.confidence >= 0.2 * top_preds[0].confidence and aspect_ratio >= 0.35:
                print(f"DEBUG: override Container Ship -> Cruise Ship because cruise score={cruise.confidence:.1f} and AR={aspect_ratio:.2f}")
                return "Cruise Ship", cruise.confidence / 100.0, top_preds
            if ferry and ferry.confidence >= 12.0 and ferry.confidence >= 0.2 * top_preds[0].confidence and aspect_ratio >= 0.30:
                print(f"DEBUG: override Container Ship -> Passenger Ferry because ferry score={ferry.confidence:.1f} and AR={aspect_ratio:.2f}")
                return "Passenger Ferry", ferry.confidence / 100.0, top_preds

        # Fishing vessel only if shape is narrow and fishing confidence is strong.
        if label == "Fishing Vessel":
            for override in ["Oil Tanker", "Container Ship", "Passenger Ferry"]:
                match = find_pred(override)
                if match and match.confidence >= 20.0 and aspect_ratio >= 2.0:
                    print(f"DEBUG: override Fishing Vessel -> {override} because AR={aspect_ratio:.2f}")
                    return override, match.confidence / 100.0, top_preds

        # If Oil Tanker or Container Ship is predicted but a Cruise Ship score is strong with a moderate aspect ratio,
        # prefer Cruise Ship because container shapes are usually flatter and cruise ships often have more vertical superstructure.
        if label in ["Oil Tanker", "Container Ship"] and cruise and cruise.confidence >= 15.0 and aspect_ratio >= 0.35:
            print(f"DEBUG: override {label} -> Cruise Ship because cruise score={cruise.confidence:.1f} and AR={aspect_ratio:.2f}")
            return "Cruise Ship", cruise.confidence / 100.0, top_preds

        return label, top_preds[0].confidence / 100.0, top_preds

    def initialize(self):
        # Stage 1: YOLO Detection
        if self.yolo_model is None:
            yolo_path = settings.YOLO_MODEL_PATH
            if not os.path.exists(yolo_path):
                fallback_yolo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "vessel_front_model.pt"))
                if os.path.exists(fallback_yolo):
                    print(f"WARNING: YOLO model not found at {yolo_path}. Falling back to {fallback_yolo}")
                    yolo_path = fallback_yolo
                else:
                    raise FileNotFoundError(f"YOLO model not found at {yolo_path}")
            print(f"DEBUG: Initializing YOLO model (Stage 1) from {yolo_path}")
            self.yolo_model = YOLO(yolo_path)
            
        # Stage 2: EfficientNetV2 Classification
        if self.classifier_model is None:
            print("DEBUG: Initializing EfficientNetV2 model (Stage 2)")
            import torch.nn as nn
            self.classifier_model = models.efficientnet_v2_s()
            num_ftrs = self.classifier_model.classifier[1].in_features
            self.classifier_model.classifier[1] = nn.Linear(num_ftrs, len(self.classes))
            
            # Load the trained weights
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "efficientnet_vessel_best.pth")
            if os.path.exists(model_path):
                device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
                self.classifier_model.load_state_dict(torch.load(model_path, map_location=device))
                self.classifier_model = self.classifier_model.to(device)
                print(f"DEBUG: Loaded fine-tuned weights from {model_path}")
            else:
                print(f"WARNING: Could not find model weights at {model_path}. Using random weights.")
                
            self.classifier_model.eval()

        # Stage 0: OOD Filter using base COCO model (if available)
        if not hasattr(self, 'ood_model'):
            ood_path = os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n.pt")
            if os.path.exists(ood_path):
                self.ood_model = YOLO(ood_path)
            else:
                self.ood_model = None

    def detect(self, image: np.ndarray) -> list[DetectionResult]:
        self.initialize()
        print("DEBUG: YOLO input image shape:", image.shape)

        # Check for OOD (e.g. dark selfies, phones) using the base COCO model
        is_ood = False
        # OOD filter disabled because it incorrectly flags cruise ships as OOD
        # if getattr(self, "ood_model", None) is not None:
        #     # We use a very low confidence (15%) so we don't accidentally reject real ships.
        #     ood_results = self.ood_model.predict(image, conf=0.15, verbose=False)[0]
        #     ood_classes = [int(box.cls[0].item()) for box in ood_results.boxes]
        #     # COCO classes: 8=boat
        #     # If the base model CANNOT find a boat anywhere in the image, it's Out-Of-Dataset.
        #     if 8 not in ood_classes:
        #         is_ood = True
        #         print("DEBUG: OOD detected (No boat found by COCO).")

        # Stage 1: Detect bounding boxes
        results = self.yolo_model.predict(
            image,
            conf=settings.YOLO_CONFIDENCE_THRESHOLD,
            iou=settings.YOLO_IOU_THRESHOLD,
            verbose=False,
            imgsz=settings.YOLO_IMAGE_SIZE,
            max_det=settings.YOLO_MAX_DETECTIONS,
        )

        res = results[0]
        if len(res.boxes) == 0 and settings.YOLO_USE_FALLBACK:
            res = self.yolo_model.predict(
                image,
                conf=settings.YOLO_FALLBACK_CONFIDENCE_THRESHOLD,
                iou=settings.YOLO_IOU_THRESHOLD,
                verbose=False,
                imgsz=settings.YOLO_IMAGE_SIZE,
                max_det=settings.YOLO_MAX_DETECTIONS,
            )[0]

        # Since we now filter non-boat objects by class ID directly, we no longer need
        # to arbitrarily drop classifications just because YOLO is less confident (e.g. distant ships).
        CLASSIFICATION_THRESHOLD = 0.01

        detections = []
        for box in res.boxes:
            confidence = float(box.conf.item()) if hasattr(box.conf, "item") else float(box.conf[0].item())
            class_id = int(box.cls.item()) if hasattr(box.cls, "item") else int(box.cls[0].item())

            if confidence < settings.YOLO_MIN_ACCEPTED_CONFIDENCE:
                continue
                
            # Filter out non-vessel objects
            is_coco = len(self.yolo_model.names) == 80
            if is_coco and class_id != 8: # 8 is 'boat' in COCO
                continue
            elif not is_coco and class_id != 0: # 0 is 'front_vessel' in custom model
                continue

            coords = box.xyxy[0].tolist()
            x_min, y_min, x_max, y_max = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])

            top_preds = []
            final_label = "Unknown"
            final_conf = confidence
            
            # If the base COCO model confirmed it's a person/phone, force it to Unknown
            if is_ood:
                confidence = 0.0  # Force skip classification
            
            if confidence >= CLASSIFICATION_THRESHOLD:
                import cv2
                
                # Letterbox padding to prevent aspect ratio distortion
                # We expand the crop from the original image to capture real background
                # instead of using BORDER_REPLICATE which smears the ship's hull!
                h = y_max - y_min
                w = x_max - x_min
                target_size = int(max(h, w) * 1.15)
                
                center_x = (x_min + x_max) // 2
                center_y = (y_min + y_max) // 2
                
                new_x_min = center_x - target_size // 2
                new_y_min = center_y - target_size // 2
                new_x_max = new_x_min + target_size
                new_y_max = new_y_min + target_size
                
                img_h, img_w = image.shape[:2]
                valid_x_min = max(0, new_x_min)
                valid_y_min = max(0, new_y_min)
                valid_x_max = min(img_w, new_x_max)
                valid_y_max = min(img_h, new_y_max)
                
                valid_crop = image[valid_y_min:valid_y_max, valid_x_min:valid_x_max]
                
                if valid_crop.size > 0:
                    pad_top = valid_y_min - new_y_min
                    pad_bottom = new_y_max - valid_y_max
                    pad_left = valid_x_min - new_x_min
                    pad_right = new_x_max - valid_x_max
                    
                    # Pad with white color to match the dataset
                    crop_padded = cv2.copyMakeBorder(valid_crop, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                    
                    crop_rgb = cv2.cvtColor(crop_padded, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(crop_rgb)
                    
                    input_tensor = self.transform(pil_img).unsqueeze(0)
                    device = next(self.classifier_model.parameters()).device
                    input_tensor = input_tensor.to(device)
                    
                    with torch.no_grad():
                        outputs = self.classifier_model(input_tensor)
                        probabilities = F.softmax(outputs, dim=1)[0]
                        
                        # Get Top 3 predictions
                        top3_prob, top3_catid = torch.topk(probabilities, 3)
                        
                        for i in range(3):
                            prob = top3_prob[i].item()
                            cat_name = self.classes[top3_catid[i].item()]
                            top_preds.append(TopPrediction(**{"class": cat_name, "confidence": round(prob * 100, 2)}))
                            
                        final_label = top_preds[0].class_name
                        final_conf = top_preds[0].confidence / 100.0
                        
                        if final_conf < 0.20:
                            global_label, global_conf, global_preds = self.classify_full_image(image)
                            print(f"DEBUG: crop classification low ({final_conf:.2f}); falling back to whole-image label {global_label} ({global_conf:.2f})")
                            final_label = global_label
                            final_conf = global_conf
                            top_preds = global_preds

            if final_label == "Unknown" or not top_preds:
                global_label, global_conf, global_preds = self.classify_full_image(image)
                print(f"DEBUG: crop result unknown; using whole-image classifier => {global_label} ({global_conf:.2f})")
                final_label = global_label
                final_conf = global_conf
                top_preds = global_preds

            bounding_box = BoundingBox(
                x_min=coords[0],
                y_min=coords[1],
                x_max=coords[2],
                y_max=coords[3]
            )

            final_label, final_conf, top_preds = self.refine_detection_label(final_label, top_preds, bounding_box)
            detections.append(DetectionResult(
                label=final_label,
                confidence=final_conf,
                bounding_box=bounding_box,
                top_predictions=top_preds
            ))

        return detections

inference_service = InferenceService()
