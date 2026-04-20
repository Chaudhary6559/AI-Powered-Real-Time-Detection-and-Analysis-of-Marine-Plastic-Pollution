"""
services/preprocess.py – Image validation and preprocessing pipeline.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
MAX_FILE_BYTES = 16 * 1024 * 1024   # 16 MB


def allowed_file(filename: str) -> bool:
    """Return True if *filename* has a supported image extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def validate_image(filepath: Path) -> tuple[bool, str]:
    """
    Validate that *filepath* is a readable image within size limits.

    Returns:
        (True, "") on success  or  (False, error_message)
    """
    if not filepath.exists():
        return False, "File does not exist."
    if filepath.stat().st_size > MAX_FILE_BYTES:
        return False, "File exceeds 16 MB limit."
    img = cv2.imread(str(filepath))
    if img is None:
        return False, "Cannot read image — unsupported format or corrupted file."
    return True, ""


def load_and_preprocess(filepath: Path, target_size: int = 640) -> np.ndarray:
    """
    Read an image from disk and prepare it for YOLO inference.

    Steps:
      1. Read as BGR (OpenCV default).
      2. Resize longest edge to *target_size* with letterbox padding.
      3. Normalise pixel values to [0, 1] float32.

    Returns:
        Preprocessed BGR numpy array (H, W, 3) as float32.
    """
    img = cv2.imread(str(filepath))
    if img is None:
        raise ValueError(f"Cannot read image at '{filepath}'.")

    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Letterbox padding to exactly target_size × target_size
    canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
    pad_top  = (target_size - new_h) // 2
    pad_left = (target_size - new_w) // 2
    canvas[pad_top : pad_top + new_h, pad_left : pad_left + new_w] = img_resized

    return canvas.astype(np.float32) / 255.0


def read_image_bgr(filepath: Path) -> np.ndarray:
    """Read an image as-is (uint8 BGR). Used for annotation drawing."""
    img = cv2.imread(str(filepath))
    if img is None:
        raise ValueError(f"Cannot read image at '{filepath}'.")
    return img
