import os
import cv2
import torch
from ultralytics import YOLO
from app.core.config import settings

# Patch torch.load to ensure compatibility with PyTorch 2.6+ and ultralytics checkpoint loading.
_original_torch_load = torch.load

def _custom_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

torch.load = _custom_torch_load

print("Model Path:", settings.YOLO_MODEL_PATH)
print("Exists:", os.path.exists(settings.YOLO_MODEL_PATH))
print("Image Size:", settings.YOLO_IMAGE_SIZE)
print("Confidence Threshold:", settings.YOLO_CONFIDENCE_THRESHOLD)
print("Fallback Threshold:", settings.YOLO_FALLBACK_CONFIDENCE_THRESHOLD)
print("IOU Threshold:", settings.YOLO_IOU_THRESHOLD)
print("Use Fallback:", settings.YOLO_USE_FALLBACK)
print("Min Accepted Confidence:", settings.YOLO_MIN_ACCEPTED_CONFIDENCE)

model = YOLO(settings.YOLO_MODEL_PATH)
print("Model:", model)
print("Model Names:", model.names)

for sample in ["ship1.jpeg", "ship2.jpeg", "dataset/val/images/IMG_20260714_142318.jpg"]:
    if not os.path.exists(sample):
        print(f"Sample missing: {sample}")
        continue
    img = cv2.imread(sample)
    print(f"\n--- {sample} ---")
    print("Image Shape:", img.shape if img is not None else None)

    for conf in [settings.YOLO_CONFIDENCE_THRESHOLD, settings.YOLO_FALLBACK_CONFIDENCE_THRESHOLD, 0.005]:
        results = model.predict(img, conf=conf, iou=settings.YOLO_IOU_THRESHOLD, verbose=False, imgsz=settings.YOLO_IMAGE_SIZE)
        res = results[0]
        print(f"\nconf={conf} count={len(res.boxes)}")
        if len(res.boxes) > 0:
            print(" max confidence:", float(res.boxes.conf.max().item()))
            print(" cls sample:", [int(x.item()) for x in res.boxes.cls[:5]])
            print(" conf sample:", [float(x.item()) for x in res.boxes.conf[:5]])
            print(" xyxy sample:", [x.tolist() for x in res.boxes.xyxy[:2]])

    if settings.YOLO_USE_FALLBACK:
        fallback = model.predict(img, conf=settings.YOLO_FALLBACK_CONFIDENCE_THRESHOLD, iou=settings.YOLO_IOU_THRESHOLD, verbose=False, imgsz=settings.YOLO_IMAGE_SIZE)
        res_fallback = fallback[0]
        print("\nFallback count:", len(res_fallback.boxes))
        if len(res_fallback.boxes) > 0:
            print("Fallback best confidence:", float(res_fallback.boxes.conf.max().item()))
