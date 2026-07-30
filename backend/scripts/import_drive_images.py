import argparse
import shutil
from pathlib import Path

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff', '.heic', '.heif'}


def copy_images(source_dir: Path, target_class: str, root_dir: Path | None = None) -> list[Path]:
    if root_dir is None:
        root_dir = Path(__file__).resolve().parents[1]

    dataset_dir = root_dir / 'dataset' / 'classifier'
    target_dir = dataset_dir / target_class
    target_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[Path] = []
    skipped_files: list[Path] = []

    for item in sorted(source_dir.iterdir()):
        if not item.is_file():
            continue

        if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
            skipped_files.append(item)
            continue

        destination = target_dir / item.name
        if destination.exists():
            stem = item.stem
            suffix = item.suffix
            counter = 1
            while True:
                destination = target_dir / f"{stem}_{counter}{suffix}"
                if not destination.exists():
                    break
                counter += 1

        shutil.copy2(item, destination)
        copied_files.append(destination)

    return copied_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Copy downloaded images into the classifier dataset for a target class.')
    parser.add_argument('--source', required=True, help='Directory containing the downloaded images to import.')
    parser.add_argument('--class', required=True, help='Target classifier class folder, e.g. Oil Tanker.')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    source_dir = Path(args.source).resolve()
    if not source_dir.exists():
        raise SystemExit(f'Source directory not found: {source_dir}')

    copied = copy_images(source_dir, args.class)
    print(f'Imported {len(copied)} file(s) into class {args.class}.')
    if not copied:
        print('No supported image files were copied.')
