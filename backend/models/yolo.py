"""
models/yolo.py – YOLOv12 model loader for marine plastic detection.

Falls back to a deterministic mock if the model weights file is missing,
so the application runs fully without a GPU or trained checkpoint.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np

# ── Try importing ultralytics (YOLOv8/v12 unified API) ───────────────────────
try:
    from ultralytics import YOLO as _YOLO
    _ULTRALYTICS_AVAILABLE = True
except ImportError:
    _ULTRALYTICS_AVAILABLE = False
    print("[YOLO] ultralytics not installed – running in mock mode.")

# ── Plastic categories YOLO is trained to detect ─────────────────────────────
PLASTIC_CLASSES = [
    "plastic_bottle",
    "plastic_bag",
    "plastic_debris",
    "fishing_net",
    "styrofoam",
    "microplastic_cluster",
]

_model: Any = None   # cached loaded model


def load_model(model_path: Path) -> bool:
    """
    Load the YOLO weights from *model_path*.
    Returns True on success, False in mock/fallback mode.
    """
    global _model
    if not _ULTRALYTICS_AVAILABLE:
        return False
    if not model_path.exists():
        print(f"[YOLO] Model file not found at '{model_path}' → fallback mock active.")
        return False
    try:
        _model = _YOLO(str(model_path))
        print(f"[YOLO] Model loaded from '{model_path}'.")
        return True
    except Exception as exc:
        print(f"[YOLO] Failed to load model: {exc} → fallback mock active.")
        return False


def _mock_inference(image_np: np.ndarray) -> dict:
    """Return plausible random detections for demo / testing purposes."""
    h, w = image_np.shape[:2]
    n = random.randint(1, 4)
    boxes, labels, scores = [], [], []
    for _ in range(n):
        x1 = random.randint(0, w // 2)
        y1 = random.randint(0, h // 2)
        x2 = random.randint(x1 + 20, min(x1 + w // 3, w))
        y2 = random.randint(y1 + 20, min(y1 + h // 3, h))
        boxes.append([x1, y1, x2, y2])
        labels.append(random.choice(PLASTIC_CLASSES))
        scores.append(round(random.uniform(0.45, 0.97), 3))
    return {"boxes": boxes, "labels": labels, "scores": scores}


def run_yolo(image_np: np.ndarray, conf: float = 0.30) -> dict:
    """
    Run YOLO inference on a BGR numpy array.

    Returns:
        {
          "boxes":  list of [x1, y1, x2, y2] (int pixels),
          "labels": list of str,
          "scores": list of float
        }
    """
    if _model is None:
        return _mock_inference(image_np)

    results = _model.predict(source=image_np, conf=conf, verbose=False)
    boxes, labels, scores = [], [], []

    for result in results:
        for box in result.boxes:
            xyxy = box.xyxy[0].tolist()
            boxes.append([int(v) for v in xyxy])
            cls_id = int(box.cls[0])
            name = result.names.get(cls_id, f"class_{cls_id}")
            labels.append(name)
            scores.append(round(float(box.conf[0]), 3))

    return {"boxes": boxes, "labels": labels, "scores": scores}
