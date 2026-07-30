import os
from pathlib import Path
from ultralytics import YOLO
import torch

# Fix PyTorch 2.6 loading issue
_original_load = torch.load
def safe_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = safe_load

def auto_label():
    model = YOLO('yolov8n.pt')
    raw_dir = Path('dataset/raw')
    
    valid_extensions = ['.jpg', '.jpeg', '.png']
    images = [f for f in raw_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]
    
    print(f"Found {len(images)} images to process...")
    
    labeled_count = 0
    for img_path in images:
        results = model(str(img_path), verbose=False)
        result = results[0] # assuming batch size 1
        
        # Open txt file for writing
        txt_path = img_path.with_suffix('.txt')
        lines = []
        
        for box in result.boxes:
            # check if it's a boat (class 8 in COCO)
            cls_id = int(box.cls[0].item())
            if cls_id == 8: # boat
                # YOLO format: class x_center y_center width height (normalized)
                x, y, w, h = box.xywhn[0].tolist()
                lines.append(f"0 {x} {y} {w} {h}\n") # map to class 0 (front_vessel)
                
        if lines:
            with open(txt_path, 'w') as f:
                f.writelines(lines)
            labeled_count += 1
            
    print(f"Finished auto-labeling. Created labels for {labeled_count} images out of {len(images)}.")

if __name__ == '__main__':
    auto_label()
