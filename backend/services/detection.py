"""
services/detection.py – Full detection pipeline orchestrator.

Coordinates:
  1. Image load (raw BGR for annotation)
  2. YOLO bounding-box detection
  3. ResNet-50 plastic-type classification per crop
  4. Annotation drawing (bounding boxes + labels on the source image)
  5. Saving annotated image to static/annotated/
  6. Persisting detection record to SQLite
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from models import yolo as yolo_model
from models import resnet as cnn_model
from services.preprocess import read_image_bgr
from database.db import execute_db

# ── Colour palette for bounding boxes (BGR) ──────────────────────────────────
BOX_COLOUR   = (0, 230, 255)   # cyan-ish  (#99f7ff in BGR approx.)
TEXT_COLOUR  = (10,  10,  10)  # dark text on light badge
BADGE_COLOUR = (0, 230, 255)


def _draw_detections(
    img: np.ndarray,
    boxes: list,
    labels: list,
    scores: list,
) -> np.ndarray:
    """Draw bounding boxes and confidence badges onto *img* (in-place copy)."""
    annotated = img.copy()
    for (x1, y1, x2, y2), label, score in zip(boxes, labels, scores):
        # Box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), BOX_COLOUR, 2)

        # Badge background
        text = f"{label}  {score:.0%}"
        (tw, th), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
        )
        badge_y = max(y1 - th - 8, 0)
        cv2.rectangle(
            annotated,
            (x1, badge_y),
            (x1 + tw + 8, badge_y + th + 6),
            BADGE_COLOUR,
            -1,
        )
        cv2.putText(
            annotated,
            text,
            (x1 + 4, badge_y + th + 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            TEXT_COLOUR,
            1,
            cv2.LINE_AA,
        )
    return annotated


def run_detection(
    image_path: Path,
    annotated_dir: Path,
    conf_threshold: float = 0.30,
    save_to_db: bool = True,
    latitude: float | None = None,
    longitude: float | None = None,
    stream_id: int | None = None,
    source: str = "upload",
) -> dict:
    """
    Full detection pipeline for one image.

    Args:
        image_path:    Path to the uploaded source image.
        annotated_dir: Directory where the annotated image will be saved.
        conf_threshold: Minimum YOLO confidence.
        save_to_db:    Persist result to SQLite detections table.
        latitude/longitude: Optional GPS coords (for geo-tagged uploads).
        stream_id:     If coming from a live stream, the stream's DB id.
        source:        "upload" | "stream"

    Returns:
        {
          "detection_id": int | None,
          "image_path": str,
          "annotated_path": str,
          "labels": [...],
          "confidences": [...],
          "bboxes": [...],
          "plastic_types": [...],
          "dominant_type": str,
          "object_count": int,
          "processing_time_ms": float
        }
    """
    t0 = time.perf_counter()

    # 1. Load raw image
    img_bgr = read_image_bgr(image_path)

    # 2. YOLO detection
    yolo_result = yolo_model.run_yolo(img_bgr, conf=conf_threshold)
    boxes   = yolo_result["boxes"]
    labels  = yolo_result["labels"]
    scores  = yolo_result["scores"]

    # 3. ResNet classification per crop
    plastic_types = []
    for x1, y1, x2, y2 in boxes:
        crop = img_bgr[max(0, y1):y2, max(0, x1):x2]
        if crop.size == 0:
            plastic_types.append({"label": "Unknown", "confidence": 0.0})
        else:
            plastic_types.append(cnn_model.classify_patch(crop))

    dominant_type = (
        plastic_types[0]["label"] if plastic_types else "No detection"
    )

    # 4. Draw annotations
    annotated = _draw_detections(img_bgr, boxes, labels, scores)

    # 5. Save annotated image
    annotated_dir.mkdir(parents=True, exist_ok=True)
    ann_filename = f"ann_{uuid.uuid4().hex[:8]}_{image_path.name}"
    ann_path = annotated_dir / ann_filename
    cv2.imwrite(str(ann_path), annotated)
    annotated_rel = f"static/annotated/{ann_filename}"

    # 6. Persist to DB
    detection_id = None
    if save_to_db:
        detection_id = execute_db(
            """INSERT INTO detections
               (image_path, annotated_path, labels, confidences, bboxes,
                plastic_type, latitude, longitude, source, stream_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(image_path),
                annotated_rel,
                json.dumps(labels),
                json.dumps(scores),
                json.dumps(boxes),
                dominant_type,
                latitude,
                longitude,
                source,
                stream_id,
            ),
        )

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "detection_id":      detection_id,
        "image_path":        str(image_path),
        "annotated_path":    annotated_rel,
        "labels":            labels,
        "confidences":       scores,
        "bboxes":            boxes,
        "plastic_types":     [pt["label"] for pt in plastic_types],
        "dominant_type":     dominant_type,
        "object_count":      len(boxes),
        "processing_time_ms": round(elapsed_ms, 1),
    }
