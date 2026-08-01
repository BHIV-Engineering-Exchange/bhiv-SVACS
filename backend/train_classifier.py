"""Train the vessel-type classifier from one folder per vessel class."""

import os
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

DATASET_DIR = Path(os.getenv("CLASSIFIER_DATASET_DIR", "dataset/classifier"))
OUTPUT_PATH = Path(os.getenv("CLASSIFIER_OUTPUT_PATH", "efficientnet_vessel_best.pth"))
EPOCHS = int(os.getenv("CLASSIFIER_EPOCHS", "10"))
BATCH_SIZE = int(os.getenv("CLASSIFIER_BATCH_SIZE", "8"))
REQUIRE_ALL_CLASSES = os.getenv("REQUIRE_ALL_VESSEL_CLASSES", "false").lower() in (
    "1", "true", "yes"
)
EXPECTED_CLASSES = [
    "Chemical Tanker",
    "Container Ship",
    "Cruise Ship",
    "Fishing Trawler",
    "Fishing Vessel",
    "LPG Carrier",
    "Oil Tanker",
    "Passenger Ferry",
]


def train_classifier() -> None:
    if not DATASET_DIR.is_dir():
        raise FileNotFoundError(f"Classifier dataset not found: {DATASET_DIR}")

    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    dataset = datasets.ImageFolder(DATASET_DIR, transform=transform)
    missing = sorted(set(EXPECTED_CLASSES) - set(dataset.classes))
    if missing and REQUIRE_ALL_CLASSES:
        raise RuntimeError(
            "Add training images for every required vessel class before training. "
            f"Missing: {', '.join(missing)}"
        )
    if missing:
        print(
            "Training available classes only; missing classes will not be predicted: "
            + ", ".join(missing)
        )
    if len(dataset) < len(dataset.classes) * 2:
        raise RuntimeError("Each vessel class needs at least two images.")

    validation_size = max(len(dataset.classes), int(len(dataset) * 0.2))
    train_size = len(dataset) - validation_size
    train_set, validation_set = random_split(
        dataset, [train_size, validation_size], generator=torch.Generator().manual_seed(42)
    )
    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    validation_loader = DataLoader(validation_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.efficientnet_v2_s(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(dataset.classes))
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    loss_function = nn.CrossEntropyLoss()
    best_accuracy = -1.0

    for epoch in range(EPOCHS):
        model.train()
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            loss_function(model(images), labels).backward()
            optimizer.step()

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for images, labels in validation_loader:
                predictions = model(images.to(device)).argmax(dim=1)
                correct += int((predictions == labels.to(device)).sum())
                total += labels.size(0)
        accuracy = correct / max(1, total)
        print(f"epoch {epoch + 1}/{EPOCHS} validation_accuracy={accuracy:.3f}")
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            torch.save({"model_state_dict": model.state_dict(), "classes": dataset.classes}, OUTPUT_PATH)

    print(f"Saved {len(dataset.classes)}-class vessel model to {OUTPUT_PATH}")


if __name__ == "__main__":
    train_classifier()
