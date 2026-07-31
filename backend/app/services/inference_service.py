"""inference_service.py — Lazy-loading YOLO + EfficientNet inference service.

CHANGES vs original:
  1. Removed module-level torch.load monkey-patch — it ran at import time and
     was a side-effect that could interfere with other libraries. The patch is
     now applied locally, only when needed, inside initialize().
  2. Added a threading.Lock around initialize() so concurrent first requests
     don't each load their own copy of YOLO (~400 MB × N).
  3. Force device = torch.device("cpu") explicitly — removes all
     torch.cuda.is_available() branches, avoids CUDA runtime init overhead.
  4. EfficientNetV2-S is constructed with weights=None instead of the default
     pretrained ImageNet download. Without a .pth file present, the original
     code would silently download ~84 MB of ImageNet weights every cold-start
     from PyTorch Hub, consuming RAM and time. We only need the architecture;
     actual vessel weights come from the local .pth file if it exists.
  5. OOD model (yolov8n.pt) is loaded only if the file is present on disk.
"""

import logging
import os
import threading
from typing import Optional

import numpy as np
import torch

# PyTorch 2.6+ changed the default of weights_only in torch.load from False to True.
# Ultralytics YOLO checkpoints contain custom class unpickling (ultralytics.nn.tasks.DetectionModel).
# We patch torch.load globally so all model unpickling (YOLO & EfficientNet) succeeds cleanly.
_orig_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _orig_torch_load(*args, **kwargs)

torch.load = _patched_torch_load

from app.core.config import settings
from app.models.schemas import DetectionResult, BoundingBox, TopPrediction

logger = logging.getLogger(__name__)

# One global lock prevents duplicate model loading under concurrent requests.
_init_lock = threading.Lock()


class InferenceService:
    def __init__(self):
        self.yolo_model = None
        self.classifier_model = None
        self.ood_model = None
        self._initialized: bool = False  # True after initialize() completes successfully
        self._init_error: Optional[str] = None  # Set if initialization fails

        self.classes = [
            "Chemical Tanker",
            "Container Ship",
            "Cruise Ship",
            "Fishing Trawler",
            "Fishing Vessel",
            "LPG Carrier",
            "Oil Tanker",
            "Passenger Ferry",
        ]

        # Build the transform once at construction time — it is pure Python/
        # torchvision and costs negligible memory (no model weights).
        # We defer the torchvision import to avoid it running at module import.

    def _get_transform(self):
        """Return (and cache) the image transform pipeline."""
        if not hasattr(self, "_transform"):
            import torchvision.transforms as transforms
            self._transform = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                    ),
                ]
            )
        return self._transform

    # ------------------------------------------------------------------
    # Model initialisation — lazy, thread-safe, idempotent
    # ------------------------------------------------------------------

    def initialize(self):
        """Load YOLO and EfficientNet models if not already loaded.

        Thread-safe: the global _init_lock prevents two concurrent requests
        from each loading a full copy of YOLO simultaneously.

        Idempotent: once self._initialized is True, this is a no-op.
        """
        # Fast path — already initialised (no lock needed, flag is read-only after set)
        if self._initialized:
            return

        with _init_lock:
            # Double-checked locking: another thread may have finished while
            # we were waiting for the lock.
            if self._initialized:
                return

            # ── Import heavy libraries here, not at module load ──────────
            import torch
            import torch.nn as nn
            import torchvision.models as models

            # Force CPU — Render Free is CPU-only; this skips all CUDA init.
            device = torch.device("cpu")

            # ── Stage 1: YOLO vessel-detection model ─────────────────────
            if self.yolo_model is None:
                yolo_path = settings.YOLO_MODEL_PATH
                logger.info("Looking for YOLO model at: %s", yolo_path)

                if not os.path.exists(yolo_path):
                    fallback_yolo = os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__), "..", "..", "vessel_front_model.pt"
                        )
                    )
                    if os.path.exists(fallback_yolo):
                        logger.warning(
                            "YOLO model not found at %s — falling back to %s",
                            yolo_path,
                            fallback_yolo,
                        )
                        yolo_path = fallback_yolo
                    else:
                        msg = (
                            f"YOLO model not found at '{yolo_path}' or fallback "
                            f"'{fallback_yolo}'. Cannot run detection."
                        )
                        logger.error(msg)
                        raise FileNotFoundError(msg)

                try:
                    # Import YOLO here, not at module level, so the Ultralytics
                    # package (and its own heavy imports) only load on first use.
                    from ultralytics import YOLO

                    logger.info("Loading YOLO model from: %s", yolo_path)
                    self.yolo_model = YOLO(yolo_path, task="detect", verbose=False)
                    logger.info("YOLO model loaded successfully.")
                except Exception as exc:
                    logger.exception("YOLO model failed to load: %s", exc)
                    raise RuntimeError(f"YOLO load failed: {exc}") from exc

            # ── Stage 2: EfficientNetV2-S classifier ─────────────────────
            if self.classifier_model is None:
                try:
                    model_path = os.path.abspath(settings.CLASSIFIER_MODEL_PATH)
                    if not os.path.exists(model_path):
                        logger.error(
                            "EfficientNet checkpoint not found at '%s'. "
                            "Ship-type classification is unavailable; refusing "
                            "to run random weights.",
                            model_path,
                        )
                        self.classifier_model = None
                    else:
                        logger.info("Building EfficientNetV2-S classifier architecture ...")
                        self.classifier_model = models.efficientnet_v2_s(weights=None)
                        num_ftrs = self.classifier_model.classifier[1].in_features
                        self.classifier_model.classifier[1] = nn.Linear(
                            num_ftrs, len(self.classes)
                        )

                        # Apply the weights_only=False patch locally — only here
                        # where it is needed, not as a global monkey-patch.
                        _orig_load = torch.load

                        def _safe_load(*args, **kwargs):
                            kwargs["weights_only"] = False
                            return _orig_load(*args, **kwargs)

                        self.classifier_model.load_state_dict(
                            _safe_load(model_path, map_location=device)
                        )
                        logger.info(
                            "EfficientNetV2-S: fine-tuned weights loaded from %s", model_path
                        )

                        self.classifier_model = self.classifier_model.to(device)
                        self.classifier_model.eval()
                        logger.info("EfficientNetV2-S classifier ready (device=cpu).")

                except Exception as exc:
                    logger.exception("EfficientNetV2-S classifier failed to load: %s", exc)
                    raise RuntimeError(f"EfficientNet load failed: {exc}") from exc

            # ── Stage 0: Base COCO OOD filter (optional) ─────────────────
            if self.ood_model is None:
                ood_path = os.path.abspath(
                    os.path.join(
                        os.path.dirname(__file__), "..", "..", "yolov8n.pt"
                    )
                )
                if os.path.exists(ood_path):
                    try:
                        from ultralytics import YOLO as _YOLO
                        self.ood_model = _YOLO(ood_path, task="detect", verbose=False)
                        logger.info("OOD filter model loaded from: %s", ood_path)
                    except Exception as exc:
                        logger.warning("OOD model failed to load (non-fatal): %s", exc)
                        self.ood_model = None
                else:
                    logger.info(
                        "OOD model not found at '%s' — OOD filter disabled.", ood_path
                    )
                    self.ood_model = None

            # Mark fully initialised
            self._initialized = True
            logger.info("InferenceService fully initialised.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def classify_full_image(
        self, image: np.ndarray
    ) -> tuple[str, float, list[TopPrediction]]:
        """Use the EfficientNet classifier on the entire image as a fallback."""
        if self.classifier_model is None:
            logger.warning("Whole-image classification skipped: classifier is unavailable.")
            return "Unknown", 0.0, []

        import cv2
        import torch
        import torch.nn.functional as F
        from PIL import Image

        try:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(image_rgb)
            device = next(self.classifier_model.parameters()).device
            input_tensor = self._get_transform()(pil_img).unsqueeze(0).to(device)

            with torch.no_grad():
                outputs = self.classifier_model(input_tensor)
                probabilities = F.softmax(outputs, dim=1)[0]
                top3_prob, top3_catid = torch.topk(probabilities, 3)

            top_predictions = []
            for idx in range(len(top3_prob)):
                score = float(top3_prob[idx].item())
                label = self.classes[int(top3_catid[idx].item())]
                top_predictions.append(
                    TopPrediction(**{"class": label, "confidence": round(score * 100, 2)})
                )

            return (
                top_predictions[0].class_name,
                top_predictions[0].confidence / 100.0,
                top_predictions,
            )
        except Exception as exc:
            logger.exception("classify_full_image() raised an exception: %s", exc)
            return "Unknown", 0.0, []

    def refine_detection_label(
        self,
        label: str,
        top_preds: list[TopPrediction],
        bbox: BoundingBox,
    ) -> tuple[str, float, list[TopPrediction]]:
        """Apply shape and probability-based overrides for common ship-type confusion."""
        if not top_preds:
            return label, 0.0, top_preds

        aspect_ratio = (bbox.x_max - bbox.x_min) / max(1.0, bbox.y_max - bbox.y_min)

        def find_pred(name: str) -> Optional[TopPrediction]:
            return next((p for p in top_preds if p.class_name == name), None)

        cruise = find_pred("Cruise Ship")
        ferry = find_pred("Passenger Ferry")
        fishing = find_pred("Fishing Vessel")

        # Cruise / Ferry vs Container confusion
        if label == "Container Ship":
            if (
                cruise
                and cruise.confidence >= 12.0
                and cruise.confidence >= 0.2 * top_preds[0].confidence
                and aspect_ratio >= 0.35
            ):
                logger.debug(
                    "Override Container Ship -> Cruise Ship (cruise=%.1f, AR=%.2f)",
                    cruise.confidence,
                    aspect_ratio,
                )
                return "Cruise Ship", cruise.confidence / 100.0, top_preds
            if (
                ferry
                and ferry.confidence >= 12.0
                and ferry.confidence >= 0.2 * top_preds[0].confidence
                and aspect_ratio >= 0.30
            ):
                logger.debug(
                    "Override Container Ship -> Passenger Ferry (ferry=%.1f, AR=%.2f)",
                    ferry.confidence,
                    aspect_ratio,
                )
                return "Passenger Ferry", ferry.confidence / 100.0, top_preds

        # Fishing vessel only if shape is narrow and fishing confidence is strong
        if label == "Fishing Vessel":
            for override in ["Oil Tanker", "Container Ship", "Passenger Ferry"]:
                match = find_pred(override)
                if match and match.confidence >= 20.0 and aspect_ratio >= 2.0:
                    logger.debug(
                        "Override Fishing Vessel -> %s (AR=%.2f)", override, aspect_ratio
                    )
                    return override, match.confidence / 100.0, top_preds

        if label in ["Oil Tanker", "Container Ship"] and cruise and cruise.confidence >= 15.0 and aspect_ratio >= 0.35:
            logger.debug(
                "Override %s -> Cruise Ship (cruise=%.1f, AR=%.2f)",
                label,
                cruise.confidence,
                aspect_ratio,
            )
            return "Cruise Ship", cruise.confidence / 100.0, top_preds

        return label, top_preds[0].confidence / 100.0, top_preds

    # ------------------------------------------------------------------
    # Main detection entry-point
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> list[DetectionResult]:
        """Run YOLO detection + EfficientNet classification on a BGR numpy image.

        Every stage is wrapped in try/except so a single failure returns partial
        results (or an empty list) instead of a 500/502.
        """
        import torch
        import torch.nn.functional as F
        from PIL import Image

        # --- Validate input ---
        if image is None or image.size == 0:
            logger.error("detect() received an empty or None image.")
            raise ValueError("Input image is empty — cannot run detection.")

        logger.info("detect() called — image shape: %s, dtype: %s", image.shape, image.dtype)

        # --- Ensure models are loaded (lazy, thread-safe) ---
        try:
            self.initialize()
        except Exception as exc:
            logger.exception("Model initialisation failed in detect(): %s", exc)
            raise

        # --- OOD filter (disabled — kept for reference) ---
        is_ood = False

        # --- Stage 1: YOLO bounding-box detection ---
        try:
            logger.info("Running YOLO predict (conf=%.2f)...", settings.YOLO_CONFIDENCE_THRESHOLD)
            results = self.yolo_model.predict(
                image,
                conf=settings.YOLO_CONFIDENCE_THRESHOLD,
                iou=settings.YOLO_IOU_THRESHOLD,
                verbose=False,
                imgsz=settings.YOLO_IMAGE_SIZE,
                max_det=settings.YOLO_MAX_DETECTIONS,
            )
            res = results[0]
            logger.info("YOLO returned %d raw boxes.", len(res.boxes))

            if len(res.boxes) == 0 and settings.YOLO_USE_FALLBACK:
                logger.info(
                    "No detections at primary threshold — retrying with fallback conf=%.2f",
                    settings.YOLO_FALLBACK_CONFIDENCE_THRESHOLD,
                )
                res = self.yolo_model.predict(
                    image,
                    conf=settings.YOLO_FALLBACK_CONFIDENCE_THRESHOLD,
                    iou=settings.YOLO_IOU_THRESHOLD,
                    verbose=False,
                    imgsz=settings.YOLO_IMAGE_SIZE,
                    max_det=settings.YOLO_MAX_DETECTIONS,
                )[0]
                logger.info("Fallback YOLO returned %d boxes.", len(res.boxes))
        except Exception as exc:
            logger.exception("YOLO predict() raised an exception: %s", exc)
            raise RuntimeError(f"YOLO inference failed: {exc}") from exc

        # CLASSIFICATION_THRESHOLD: keep even low-confidence detections for classification
        CLASSIFICATION_THRESHOLD = 0.01

        detections: list[DetectionResult] = []

        for box in res.boxes:
            try:
                confidence = (
                    float(box.conf.item())
                    if hasattr(box.conf, "item")
                    else float(box.conf[0].item())
                )
                class_id = (
                    int(box.cls.item())
                    if hasattr(box.cls, "item")
                    else int(box.cls[0].item())
                )

                if confidence < settings.YOLO_MIN_ACCEPTED_CONFIDENCE:
                    continue

                # Filter out non-vessel objects
                is_coco = len(self.yolo_model.names) == 80
                if is_coco and class_id != 8:  # 8 = 'boat' in COCO
                    continue
                elif not is_coco and class_id != 0:  # 0 = 'front_vessel' in custom model
                    continue

                coords = box.xyxy[0].tolist()
                x_min = int(coords[0])
                y_min = int(coords[1])
                x_max = int(coords[2])
                y_max = int(coords[3])

                top_preds: list[TopPrediction] = []
                # The bundled YOLO checkpoint is COCO-trained, so its vessel
                # class is the generic "boat". Preserve that detection when
                # the optional ship-type classifier is unavailable.
                final_label = "Boat" if self.classifier_model is None else "Unknown"
                final_conf = confidence

                if is_ood:
                    confidence = 0.0  # Force skip classification

                # --- Stage 2: EfficientNet crop classification ---
                if confidence >= CLASSIFICATION_THRESHOLD and self.classifier_model is not None:
                    try:
                        import cv2

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

                            crop_padded = cv2.copyMakeBorder(
                                valid_crop,
                                pad_top,
                                pad_bottom,
                                pad_left,
                                pad_right,
                                cv2.BORDER_CONSTANT,
                                value=(255, 255, 255),
                            )

                            crop_rgb = cv2.cvtColor(crop_padded, cv2.COLOR_BGR2RGB)
                            pil_img = Image.fromarray(crop_rgb)

                            input_tensor = self._get_transform()(pil_img).unsqueeze(0)
                            device = next(self.classifier_model.parameters()).device
                            input_tensor = input_tensor.to(device)

                            with torch.no_grad():
                                outputs = self.classifier_model(input_tensor)
                                probabilities = F.softmax(outputs, dim=1)[0]
                                top3_prob, top3_catid = torch.topk(probabilities, 3)

                                for i in range(3):
                                    prob = top3_prob[i].item()
                                    cat_name = self.classes[top3_catid[i].item()]
                                    top_preds.append(
                                        TopPrediction(
                                            **{
                                                "class": cat_name,
                                                "confidence": round(prob * 100, 2),
                                            }
                                        )
                                    )

                                final_label = top_preds[0].class_name
                                final_conf = top_preds[0].confidence / 100.0
                                logger.debug(
                                    "Crop classification => %s (%.2f)", final_label, final_conf
                                )

                                if final_conf < 0.20:
                                    logger.debug(
                                        "Crop confidence low (%.2f) — falling back to whole-image classifier.",
                                        final_conf,
                                    )
                                    global_label, global_conf, global_preds = self.classify_full_image(image)
                                    logger.info(
                                        "Whole-image fallback => %s (%.2f)", global_label, global_conf
                                    )
                                    final_label = global_label
                                    final_conf = global_conf
                                    top_preds = global_preds
                        else:
                            logger.warning("Crop is empty — skipping classification for this box.")

                    except Exception as exc:
                        logger.exception(
                            "EfficientNet crop classification failed for box %s: %s", coords, exc
                        )
                        # Fall back to whole-image
                        final_label, final_conf, top_preds = self.classify_full_image(image)

                # --- Whole-image fallback if label is still Unknown ---
                if (final_label == "Unknown" or not top_preds) and self.classifier_model is not None:
                    try:
                        global_label, global_conf, global_preds = self.classify_full_image(image)
                        logger.info(
                            "Crop result unknown — using whole-image classifier => %s (%.2f)",
                            global_label,
                            global_conf,
                        )
                        final_label = global_label
                        final_conf = global_conf
                        top_preds = global_preds
                    except Exception as exc:
                        logger.exception("Whole-image fallback also failed: %s", exc)

                bounding_box = BoundingBox(
                    x_min=coords[0],
                    y_min=coords[1],
                    x_max=coords[2],
                    y_max=coords[3],
                )

                if top_preds:
                    final_label, final_conf, top_preds = self.refine_detection_label(
                        final_label, top_preds, bounding_box
                    )

                detections.append(
                    DetectionResult(
                        label=final_label,
                        confidence=final_conf,
                        bounding_box=bounding_box,
                        top_predictions=top_preds,
                    )
                )

            except Exception as exc:
                logger.exception("Skipping box due to unexpected error: %s", exc)
                continue

        logger.info("detect() finished — %d detection(s) returned.", len(detections))
        return detections


inference_service = InferenceService()
