import os
import torch
import torch.nn as nn
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
from tqdm import tqdm
from PIL import ImageFile
import PIL.Image

# Prevent PIL from crashing
ImageFile.LOAD_TRUNCATED_IMAGES = True
PIL.Image.MAX_IMAGE_PIXELS = None

def evaluate(data_dir="dataset/classifier", model_path="efficientnet_vessel_best.pth", batch_size=32):
    if not os.path.exists(data_dir):
        print(f"Error: Dataset directory {data_dir} not found.")
        return

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    full_dataset = datasets.ImageFolder(data_dir, transform=transform)
    dataloader = DataLoader(full_dataset, batch_size=batch_size, shuffle=False, num_workers=4)
    
    class_names = full_dataset.classes
    num_classes = len(class_names)
    
    model = models.efficientnet_v2_s()
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    
    model.load_state_dict(torch.load(model_path, map_location=device))
    model = model.to(device)
    model.eval()

    class_correct = {classname: 0 for classname in class_names}
    class_total = {classname: 0 for classname in class_names}

    print(f"Evaluating model on all {len(full_dataset)} images across {num_classes} classes...")
    
    with torch.no_grad():
        for inputs, labels in tqdm(dataloader):
            inputs = inputs.to(device)
            labels = labels.to(device)
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            
            for i in range(len(labels)):
                label = labels[i].item()
                pred = preds[i].item()
                classname = class_names[label]
                class_total[classname] += 1
                if label == pred:
                    class_correct[classname] += 1

    print("\n" + "="*45)
    print("           CLASS-WISE PREDICTION ACCURACY")
    print("="*45)
    total_correct = 0
    total_samples = 0
    for classname in class_names:
        if class_total[classname] > 0:
            accuracy = 100 * class_correct[classname] / class_total[classname]
            total_correct += class_correct[classname]
            total_samples += class_total[classname]
            print(f"{classname:20s}: {accuracy:6.2f}% ({class_correct[classname]:3d} / {class_total[classname]:3d} correct)")
        else:
            print(f"{classname:20s}: No images found")
            
    print("-" * 45)
    overall_acc = 100 * total_correct / total_samples
    print(f"{'OVERALL ACCURACY':20s}: {overall_acc:6.2f}% ({total_correct:3d} / {total_samples:3d} correct)")
    print("=" * 45)

if __name__ == '__main__':
    evaluate()
