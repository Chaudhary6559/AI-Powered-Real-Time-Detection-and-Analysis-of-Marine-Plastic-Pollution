"""
models/resnet.py – ResNet-50 classifier for marine plastic type refinement.

Loaded via TensorFlow/Keras (.h5 or SavedModel).
Falls back to a mock classifier if the model file is missing.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np

# ── Try importing TensorFlow ──────────────────────────────────────────────────
try:
    import tensorflow as tf  # noqa: F401
    from tensorflow import keras
    _TF_AVAILABLE = True
except ImportError:
    _TF_AVAILABLE = False
    print("[ResNet] TensorFlow not installed – running in mock mode.")

# ── Plastic type labels ───────────────────────────────────────────────────────
PLASTIC_TYPES = [
    "PET Bottle",
    "HDPE Container",
    "Plastic Film / Bag",
    "Fishing Net / Rope",
    "Styrofoam / EPS",
    "Mixed Rigid Plastic",
    "Microplastic Cluster",
]

_model: Any = None


def load_model(model_path: Path) -> bool:
    """Load Keras model from *model_path* (.h5 or SavedModel directory)."""
    global _model
    if not _TF_AVAILABLE:
        return False
    if not model_path.exists():
        print(f"[ResNet] Model not found at '{model_path}' → fallback mock active.")
        return False
    try:
        _model = keras.models.load_model(str(model_path))
        print(f"[ResNet] Model loaded from '{model_path}'.")
        return True
    except Exception as exc:
        print(f"[ResNet] Failed to load model: {exc} → fallback mock active.")
        return False


def _preprocess_for_resnet(image_np: np.ndarray) -> np.ndarray:
    """Resize to 224×224 and apply ImageNet normalisation."""
    import cv2
    img = cv2.resize(image_np, (224, 224))
    img = img.astype("float32")
    # ImageNet mean/std normalisation
    mean = np.array([0.485, 0.456, 0.406], dtype="float32")
    std  = np.array([0.229, 0.224, 0.225], dtype="float32")
    img = (img / 255.0 - mean) / std
    return np.expand_dims(img, axis=0)   # (1, 224, 224, 3)


def _mock_classify() -> dict:
    label = random.choice(PLASTIC_TYPES)
    confidence = round(random.uniform(0.60, 0.97), 3)
    return {"label": label, "confidence": confidence}


def classify_patch(image_np: np.ndarray) -> dict:
    """
    Classify a cropped image patch using ResNet-50.

    Returns:
        {"label": str, "confidence": float}
    """
    if _model is None:
        return _mock_classify()

    x = _preprocess_for_resnet(image_np)
    preds = _model.predict(x, verbose=0)[0]
    idx = int(np.argmax(preds))
    label = PLASTIC_TYPES[idx] if idx < len(PLASTIC_TYPES) else f"Class {idx}"
    return {"label": label, "confidence": round(float(preds[idx]), 3)}
