import argparse
import os
from collections import Counter

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, random_split, WeightedRandomSampler
from torchvision import datasets, models, transforms
from tqdm import tqdm
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

    # Data augmentation. Widened slightly vs. the previous version to give
    # more variety to classes with very few real images (some naval
    # classes currently have only ~15-20 photos) — this only reshapes
    # existing real images (crop/flip/rotate/jitter), it never invents
    # new visual content.
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224, scale=(0.65, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(20),
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.25, hue=0.1),
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

    train_dataset.dataset.transform = data_transforms['train']
    val_dataset.dataset.transform = data_transforms['val']

    class_names = full_dataset.classes
    num_classes = len(class_names)

    # ------------------------------------------------------------------
    # Class-imbalance handling.
    #
    # This dataset currently ranges from ~11 images (LPG Carrier) to
    # ~301 images (Offshore Support Vessel) per class — roughly a 27:1
    # ratio, made worse by adding 11 naval classes at ~15-20 images
    # each. Without correction, the model sees over-represented classes
    # far more often and tends to be biased toward guessing them when
    # uncertain.
    #
    # Two corrections, used together:
    #   1. WeightedRandomSampler — oversamples minority-class images
    #      during training so every class is seen roughly equally often
    #      per epoch. This does NOT create new/fake images; it just
    #      shows the same real minority-class photos more frequently.
    #   2. Class-weighted loss — penalizes misclassifying minority
    #      classes more heavily, using inverse-SQUARE-ROOT frequency
    #      (softer than full inverse frequency, to avoid over-correcting
    #      and destabilizing training on the well-represented classes).
    # ------------------------------------------------------------------
    train_targets = [full_dataset.targets[i] for i in train_dataset.indices]
    class_counts = Counter(train_targets)

    print("Training set class distribution:")
    for idx, name in enumerate(class_names):
        print(f"  {name}: {class_counts.get(idx, 0)} images")

    sample_weights = [1.0 / class_counts[t] for t in train_targets]
    sampler = WeightedRandomSampler(
        sample_weights, num_samples=len(sample_weights), replacement=True
    )

    loss_weights = torch.tensor(
        [1.0 / (class_counts.get(i, 1) ** 0.5) for i in range(num_classes)],
        dtype=torch.float,
    ).to(device)

    dataloaders = {
        'train': DataLoader(train_dataset, batch_size=batch_size, sampler=sampler, num_workers=4),
        'val': DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4)
    }

    dataset_sizes = {'train': len(train_dataset), 'val': len(val_dataset)}

    print(f"Loaded {len(full_dataset)} total images across {num_classes} classes.")
    print(f"Classes: {class_names}")

    # Load EfficientNetV2 (Small)
    print("Loading pre-trained EfficientNetV2-S model...")
    model = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)

    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(weight=loss_weights)
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
    else:
        train_classifier(data_dir=data_path, epochs=args.epochs, batch_size=args.batch_size)
