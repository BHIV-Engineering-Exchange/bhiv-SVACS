import glob
import os
import shutil
import torch
from ultralytics import YOLO

# Temporary fix for PyTorch 2.6 and ultralytics loading weights
_original_load = torch.load
def safe_load(*args, **kwargs): 
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = safe_load

RUN_NAME = os.getenv('YOLO_TRAIN_RUN_NAME', 'vessel_front')


def verify_dataset_labels():
    missing_issues = []
    for split in ['train', 'val', 'test']:
        img_dir = os.path.join('dataset', split, 'images')
        lbl_dir = os.path.join('dataset', split, 'labels')
        images = {os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(img_dir, '*'))}
        labels = {os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(lbl_dir, '*'))}

        missing_labels = sorted(images - labels)
        missing_images = sorted(labels - images)

        if missing_labels or missing_images:
            missing_issues.append((split, missing_labels, missing_images))

    if missing_issues:
        for split, missing_labels, missing_images in missing_issues:
            print(f"Dataset mismatch in '{split}' split:")
            if missing_labels:
                print(f"  Images without labels ({len(missing_labels)}): {missing_labels[:20]}")
            if missing_images:
                print(f"  Labels without images ({len(missing_images)}): {missing_images[:20]}")
        raise RuntimeError(
            'Dataset validation failed. Ensure every image has a matching label file and remove or label any unlabeled images.'
        )


def train_model():
    # verify_dataset_labels() # Disabled: YOLO supports unlabeled images as background images

    # Load a model
    model = YOLO('yolov8n.pt')  # load a pretrained model (recommended for training)

    # Train the model
    # We specify data.yaml, epochs, imgsz (image size), and project directory
    results = model.train(
        data='dataset/data.yaml',
        epochs=10,
        imgsz=640,
        batch=4,
        project='runs/detect',
        name=RUN_NAME,
        # device='cuda:0', # Recommend switching to GPU for 60 classes
        device='cpu',
        amp=False,
        augment=True,
        # Maritime robustness augmentations
        hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
        degrees=10.0, translate=0.1, scale=0.5, shear=2.0,
        perspective=0.0001, flipud=0.0, fliplr=0.5, mosaic=1.0, mixup=0.1
    )
    
    print("Training completed!")
    print("Results saved to:", results.save_dir)

    # Copy the best trained weights into the workspace root so the runtime can use them.
    weights_dir = os.path.join('runs', 'detect', RUN_NAME, 'weights')
    final_weights = 'vessel_front_model.pt'
    for candidate in ['best.pt', 'last.pt']:
        source_path = os.path.join(weights_dir, candidate)
        if os.path.exists(source_path):
            shutil.copyfile(source_path, final_weights)
            print(f"Copied trained weights to: {final_weights}")
            break
    else:
        print("Warning: could not find trained weights to copy. Check the training output directory.")

if __name__ == '__main__':
    train_model()
