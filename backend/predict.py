import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import sys
import os

def predict(image_path, model_path='efficientnet_vessel_best.pth'):
    if not os.path.exists(image_path):
        print(f"Error: Could not find image at {image_path}")
        return

    # Define classes based on dataset directory structure
    class_names = [
        'Chemical Tanker', 'Container Ship', 'Cruise Ship', 
        'Fishing Trawler', 'Fishing Vessel', 'LPG Carrier', 
        'Oil Tanker', 'Passenger Ferry'
    ]
    num_classes = len(class_names)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # Load model architecture
    model = models.efficientnet_v2_s()
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    
    # Load trained weights
    model.load_state_dict(torch.load(model_path, map_location=device))
    model = model.to(device)
    model.eval()

    # Transformation used during validation
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Load and transform image
    image = Image.open(image_path).convert("RGB")
    input_tensor = transform(image).unsqueeze(0).to(device)

    # Predict
    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        _, preds = torch.max(outputs, 1)

    predicted_class = class_names[preds[0].item()]
    confidence = probabilities[0][preds[0].item()].item() * 100

    print(f"Prediction: {predicted_class}")
    print(f"Confidence: {confidence:.2f}%")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python predict.py <path_to_image>")
    else:
        predict(sys.argv[1])
