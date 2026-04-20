"""
utils/helpers.py – Shared response helpers for all route blueprints.

Provides two thin helpers so every endpoint returns a consistent
JSON envelope without boilerplate.
"""

from __future__ import annotations

from flask import jsonify


def success(data=None, status_code: int = 200):
    """
    Build a standard success response.

    Example output:
        {"status": "success", "data": {...}}
    """
    return jsonify({"status": "success", "data": data}), status_code


def error(message: str, status_code: int = 400):
    """
    Build a standard error response.

    Example output:
        {"status": "error", "message": "..."}
    """
    return jsonify({"status": "error", "message": message}), status_code
