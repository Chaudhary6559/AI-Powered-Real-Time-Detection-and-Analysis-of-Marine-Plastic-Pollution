"""
routes/image.py – Image upload and ML analysis endpoint.

POST /analyze
  - Validates file format & size
  - Saves to uploads/
  - Runs the full detection pipeline (YOLO → ResNet)
  - Returns JSON result with annotated image path
"""

from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, request, current_app

from services.preprocess import allowed_file, validate_image
from services.detection import run_detection
from utils.helpers import success, error

image_bp = Blueprint("image", __name__)


@image_bp.post("/analyze")
def analyze():
    """POST /analyze – Upload an image and run plastic detection."""

    # ── 1. Validate file presence ─────────────────────────────────────────────
    if "file" not in request.files:
        return error("No file part in the request. Key expected: 'file'.", 400)

    file = request.files["file"]
    if file.filename == "":
        return error("No file selected.", 400)

    if not allowed_file(file.filename):
        return error(
            "Unsupported file type. Allowed: png, jpg, jpeg, webp, bmp.", 400
        )

    # ── 2. Save to uploads/ ───────────────────────────────────────────────────
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex[:10]}_{file.filename}"
    save_path   = upload_dir / unique_name
    file.save(str(save_path))

    # ── 3. Validate the saved file ────────────────────────────────────────────
    valid, msg = validate_image(save_path)
    if not valid:
        save_path.unlink(missing_ok=True)
        return error(f"Invalid image: {msg}", 400)

    # ── 4. Optional geo-tag from form fields ──────────────────────────────────
    try:
        latitude  = float(request.form.get("latitude",  0) or 0) or None
        longitude = float(request.form.get("longitude", 0) or 0) or None
    except (TypeError, ValueError):
        latitude = longitude = None

    # ── 5. Run detection pipeline ─────────────────────────────────────────────
    annotated_dir = Path(current_app.static_folder) / "annotated"
    conf          = current_app.config.get("YOLO_CONF_THRESHOLD", 0.30)

    try:
        result = run_detection(
            image_path    = save_path,
            annotated_dir = annotated_dir,
            conf_threshold= conf,
            save_to_db    = True,
            latitude      = latitude,
            longitude     = longitude,
            source        = "upload",
        )
    except Exception as exc:
        return error(f"Detection failed: {exc}", 500)

    return success(result, 200)
