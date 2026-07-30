import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

CLASS_NAMES = [
    'Chemical Tanker',
    'Container Ship',
    'Cruise Ship',
    'Fishing Trawler',
    'Fishing Vessel',
    'LPG Carrier',
    'Oil Tanker',
    'Passenger Ferry',
]

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'dataset' / 'classifier'
TRAIN_SCRIPT = BASE_DIR / 'scripts' / 'train_classifier.py'


def validate_class_name(name: str) -> str:
    if name not in CLASS_NAMES:
        raise ValueError(
            f"Unknown class '{name}'. Valid classes are: {', '.join(CLASS_NAMES)}"
        )
    return name


def copy_image_to_class(image_path: Path, class_name: str) -> Path:
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    class_dir = DATA_DIR / class_name
    class_dir.mkdir(parents=True, exist_ok=True)

    destination = class_dir / image_path.name
    if destination.exists():
        base = image_path.stem
        suffix = image_path.suffix
        counter = 1
        while True:
            destination = class_dir / f"{base}_{counter}{suffix}"
            if not destination.exists():
                break
            counter += 1

    shutil.copy2(image_path, destination)
    return destination


def train_classifier(epochs: int, batch_size: int) -> None:
    if not TRAIN_SCRIPT.exists():
        raise FileNotFoundError(f"Training script not found: {TRAIN_SCRIPT}")

    print(f"Starting classifier training with epochs={epochs}, batch_size={batch_size}...")
    result = subprocess.run(
        [sys.executable, str(TRAIN_SCRIPT), f"--epochs={epochs}", f"--batch_size={batch_size}"],
        cwd=str(BASE_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError("Classifier training failed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy an image into the classifier dataset and optionally retrain EfficientNetV2."
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to the local image file to add to the classifier dataset.",
    )
    parser.add_argument(
        "--class",
        dest="class_name",
        required=True,
        help="Target classifier class folder, e.g. 'Cruise Ship'.",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train the classifier after copying the image.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of epochs to train if --train is used.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Batch size to use during training if --train is used.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    class_name = validate_class_name(args.class_name)

    print(f"Adding image '{args.image}' to class '{class_name}'...")
    destination = copy_image_to_class(args.image, class_name)
    print(f"Copied image to: {destination}")

    if args.train:
        train_classifier(args.epochs, args.batch_size)
    else:
        print("Image added. Run training separately with --train to update the classifier.")


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
