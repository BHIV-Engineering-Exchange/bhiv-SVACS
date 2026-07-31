#!/usr/bin/env python3
"""download_ocr_models.py — Pre-download EasyOCR model weights at build time.

Run this script ONCE during the Render build step (see render.yaml buildCommand).
It downloads the detection and recognition model files into backend/ocr_models/
so that at runtime EasyOCR never needs to hit the network, and download_enabled=False
can be safely used.

Usage:
    python scripts/download_ocr_models.py

This script is intentionally simple and dependency-light. It imports easyocr
(which is already installed via requirements.txt) and calls Reader() with
download_enabled=True pointed at our target directory. EasyOCR handles the
actual download logic; we just tell it where to put the files.

Memory note:
    During the build step on Render, there is no 512 MB RAM cap, so this
    download is safe. At runtime, the models are read from disk — no download.
"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# Absolute path to the ocr_models directory relative to this script.
# Script lives at  backend/scripts/download_ocr_models.py
# Models land at   backend/ocr_models/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_MODEL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "ocr_models"))

# The language(s) to pre-download models for.
# Must match settings.OCR_LANGUAGES in app/core/config.py.
OCR_LANGUAGES = ["en"]


def main():
    os.makedirs(OCR_MODEL_DIR, exist_ok=True)
    logger.info("OCR model directory: %s", OCR_MODEL_DIR)

    try:
        import easyocr
    except ImportError:
        logger.error(
            "easyocr is not installed. Run: pip install easyocr==1.7.1"
        )
        sys.exit(1)

    logger.info(
        "Pre-downloading EasyOCR models for languages=%s into %s ...",
        OCR_LANGUAGES,
        OCR_MODEL_DIR,
    )

    try:
        # Constructing the Reader triggers the download if files are absent.
        # We set download_enabled=True here explicitly (this is the one place
        # we intentionally allow a network download — the build step).
        reader = easyocr.Reader(
            OCR_LANGUAGES,
            gpu=False,
            model_storage_directory=OCR_MODEL_DIR,
            download_enabled=True,
        )
        logger.info("EasyOCR models downloaded successfully into: %s", OCR_MODEL_DIR)

        # Verify the directory actually contains files
        files = os.listdir(OCR_MODEL_DIR)
        logger.info("Files in ocr_models/: %s", files)

        if not files:
            logger.error(
                "ocr_models/ directory is empty after download — something went wrong."
            )
            sys.exit(1)

    except Exception as exc:
        logger.exception("EasyOCR model download failed: %s", exc)
        sys.exit(1)

    logger.info("Done — OCR models are ready for production use.")


if __name__ == "__main__":
    main()
