"""
services/classification.py – Standalone plastic-type classification helper.

Wraps the ResNet model for direct classification of an uploaded
image (not crop-based) — useful for when YOLO detects nothing but
the user still wants a top-level material classification.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from models import resnet as cnn_model


def classify_image(image_path: Path) -> dict:
    """
    Classify the entire image as a plastic type.

    Returns:
        {"label": str, "confidence": float}
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return {"label": "Unknown", "confidence": 0.0}
    return cnn_model.classify_patch(img)


def classify_detections(image_path: Path, boxes: list) -> list[dict]:
    """
    Classify each bounding-box crop within an image.

    Args:
        image_path: Source image path.
        boxes:      List of [x1, y1, x2, y2] pixel boxes.

    Returns:
        List of {"label": str, "confidence": float} per box.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return [{"label": "Unknown", "confidence": 0.0}] * len(boxes)

    results = []
    for x1, y1, x2, y2 in boxes:
        crop = img[max(0, y1) : y2, max(0, x1) : x2]
        if crop.size == 0:
            results.append({"label": "Unknown", "confidence": 0.0})
        else:
            results.append(cnn_model.classify_patch(crop))
    return results
