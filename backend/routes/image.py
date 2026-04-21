"""
routes/image.py – Image & video upload and ML analysis endpoints.

POST /analyze          - Upload image → YOLO + CNN detection → JSON result
POST /analyze-video    - Upload video → extract frames → detection per frame
GET  /results          - List recent detections from DB
"""

from __future__ import annotations

import uuid
from pathlib import Path

import cv2
from flask import Blueprint, request, current_app

from services.preprocess import allowed_file, validate_image
from services.detection import run_detection
from database.db import query_db
from utils.helpers import success, error

image_bp = Blueprint("image", __name__)

ALLOWED_VIDEO_EXTS = {"mp4", "avi", "mov", "mkv", "webm"}


def _allowed_video(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTS


# ── Image analysis ────────────────────────────────────────────────────────────
@image_bp.post("/analyze")
def analyze():
    """POST /analyze – Upload image or video and run plastic detection."""

    if "file" not in request.files:
        return error("No file part in the request. Key expected: 'file'.", 400)

    file = request.files["file"]
    if file.filename == "":
        return error("No file selected.", 400)

    filename_lower = file.filename.lower()
    is_video = _allowed_video(file.filename)

    if not is_video and not allowed_file(file.filename):
        return error(
            "Unsupported file type. Images: png, jpg, jpeg, webp, bmp. "
            "Videos: mp4, avi, mov, mkv, webm.", 400
        )

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex[:10]}_{file.filename}"
    save_path = upload_dir / unique_name
    file.save(str(save_path))

    # ── Optional geo-tag ──────────────────────────────────────────────────────
    try:
        latitude  = float(request.form.get("latitude",  0) or 0) or None
        longitude = float(request.form.get("longitude", 0) or 0) or None
    except (TypeError, ValueError):
        latitude = longitude = None

    annotated_dir = Path(current_app.static_folder) / "annotated"
    conf          = current_app.config.get("YOLO_CONF_THRESHOLD", 0.30)

    if is_video:
        # ── Video: extract every Nth frame and detect ─────────────────────────
        try:
            results = _process_video(save_path, annotated_dir, conf, latitude, longitude)
        except Exception as exc:
            return error(f"Video detection failed: {exc}", 500)
        return success({"type": "video", "frames_processed": len(results), "detections": results}, 200)

    else:
        # ── Image: single detection ───────────────────────────────────────────
        valid, msg = validate_image(save_path)
        if not valid:
            save_path.unlink(missing_ok=True)
            return error(f"Invalid image: {msg}", 400)

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

        return success({"type": "image", **result}, 200)


def _process_video(video_path: Path, annotated_dir: Path, conf: float,
                   latitude, longitude, frame_interval: int = 30) -> list:
    """Extract frames from a video every frame_interval frames and run detection on each."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    results = []
    frame_count = 0
    processed = 0
    MAX_FRAMES = 20  # cap to avoid timeout

    while processed < MAX_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % frame_interval != 0:
            continue

        # Save frame as temp image
        tmp_path = video_path.parent / f"frame_{uuid.uuid4().hex[:8]}.jpg"
        cv2.imwrite(str(tmp_path), frame)

        try:
            result = run_detection(
                image_path    = tmp_path,
                annotated_dir = annotated_dir,
                conf_threshold= conf,
                save_to_db    = True,
                latitude      = latitude,
                longitude     = longitude,
                source        = "video_upload",
            )
            results.append(result)
            processed += 1
        except Exception:
            pass
        finally:
            tmp_path.unlink(missing_ok=True)

    cap.release()
    return results


# ── Recent results ─────────────────────────────────────────────────────────────
@image_bp.get("/results")
def get_results():
    """GET /results – Return recent detections."""
    limit = min(int(request.args.get("limit", 20)), 100)
    rows = query_db(
        "SELECT id, annotated_path, labels, confidences, plastic_type, "
        "source, latitude, longitude, created_at "
        "FROM detections ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    return success([dict(r) for r in rows])
