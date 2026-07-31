import argparse
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm
import time
from PIL import ImageFile
import PIL.Image

# Prevent PIL from crashing when reading partially downloaded/corrupted images
ImageFile.LOAD_TRUNCATED_IMAGES = True
# Prevent PIL from crashing on massive high-resolution Wikimedia images (DecompressionBomb)
PIL.Image.MAX_IMAGE_PIXELS = None

def train_classifier(data_dir="dataset/classifier", epochs=50, batch_size=32):
    print("Initializing EfficientNetV2 training pipeline...")
    
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Advanced Data Augmentation mapping phase 3/5 requirements
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    print(f"Loading dataset from: {os.path.abspath(data_dir)}")
    
    # ImageFolder throws FileNotFoundError if ANY directory is empty.
    # We must delete empty class directories created by the interrupted scraper.
    for folder_name in os.listdir(data_dir):
        folder_path = os.path.join(data_dir, folder_name)
        if os.path.isdir(folder_path):
            if len(os.listdir(folder_path)) == 0:
                print(f"Removing empty class directory: {folder_name}")
                os.rmdir(folder_path)

    full_dataset = datasets.ImageFolder(data_dir)
    
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    # Apply specific transforms
    train_dataset.dataset.transform = data_transforms['train']
    val_dataset.dataset.transform = data_transforms['val']

    dataloaders = {
        'train': DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4),
        'val': DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4)
    }

    dataset_sizes = {'train': len(train_dataset), 'val': len(val_dataset)}
    class_names = full_dataset.classes
    num_classes = len(class_names)
    
    print(f"Loaded {len(full_dataset)} total images across {num_classes} classes.")
    print(f"Classes: {class_names}")

    # Load EfficientNetV2 (Small)
    print("Loading pre-trained EfficientNetV2-S model...")
    model = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)
    
    # Modify final layer for our 35 classes
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

    best_acc = 0.0

    print(f"Starting training for {epochs} epochs...")
    for epoch in range(epochs):
        print(f'Epoch {epoch}/{epochs - 1}')
        print('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in tqdm(dataloaders[phase], desc=f"{phase} Phase"):
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            if phase == 'train':
                scheduler.step()

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "classes": class_names,
                    },
                    'efficientnet_vessel_best.pth',
                )
                print("Saved new best model!")

        print()

    print(f'Training complete! Best val Acc: {best_acc:4f}')
    print("Weights saved to 'efficientnet_vessel_best.pth'")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Train the ship classifier from the dataset directory."
    )
    parser.add_argument(
        "--data_dir",
        default="dataset/classifier",
        help="Path to the classifier image dataset.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of epochs to train.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Batch size for training.",
    )
    return parser.parse_args()


if __name__ == '__main__':
    # Make sure we're in the backend directory
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    args = parse_args()
    data_path = args.data_dir

    if not os.path.exists(data_path) or len(os.listdir(data_path)) == 0:
        print(f"ERROR: Dataset directory '{data_path}' is empty or does not exist.")
        print("Please run 'python scripts/scrape_wikimedia.py' first to download the images!")
    else:
        train_classifier(data_dir=data_path, epochs=args.epochs, batch_size=args.batch_size)
