"""
routes/auth.py – Authentication endpoints.

Uses Flask session + Werkzeug password hashing (no heavy JWT library needed).
All responses follow the unified {"status": ..., "data": ...} envelope.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify, session

from database.db import query_db, execute_db
from utils.helpers import success, error

auth_bp = Blueprint("auth", __name__)


# ── Register ──────────────────────────────────────────────────────────────────
@auth_bp.post("/register")
def register():
    """POST /auth/register  –  Create a new user account."""
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    email    = (body.get("email")    or "").strip().lower()
    password = body.get("password", "")
    role     = body.get("role", "analyst")

    if not username or not email or not password:
        return error("username, email, and password are required.", 400)
    if len(password) < 6:
        return error("Password must be at least 6 characters.", 400)

    # Check uniqueness
    if query_db("SELECT id FROM users WHERE username = ?", (username,), one=True):
        return error("Username already taken.", 409)
    if query_db("SELECT id FROM users WHERE email = ?", (email,), one=True):
        return error("Email already registered.", 409)

    # Hash with Werkzeug PBKDF2
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash(password)

    user_id = execute_db(
        "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (username, email, pw_hash, role),
    )
    return success({"user_id": user_id, "username": username, "role": role}, 201)


# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.post("/login")
def login():
    """POST /auth/login  –  Authenticate and open a session."""
    body     = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password", "")

    if not username or not password:
        return error("username and password are required.", 400)

    row = query_db(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?",
        (username,), one=True,
    )
    if row is None:
        return error("Invalid credentials.", 401)

    from werkzeug.security import check_password_hash
    if not check_password_hash(row["password_hash"], password):
        return error("Invalid credentials.", 401)

    session["user_id"]  = row["id"]
    session["username"] = row["username"]
    session["role"]     = row["role"]

    return success({"user_id": row["id"], "username": row["username"], "role": row["role"]})


# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.post("/logout")
def logout():
    """POST /auth/logout  –  Destroy session."""
    session.clear()
    return success({"message": "Logged out successfully."})


# ── Current user ──────────────────────────────────────────────────────────────
@auth_bp.get("/me")
def me():
    """GET /auth/me  –  Return current session user."""
    user_id = session.get("user_id")
    if not user_id:
        return error("Not authenticated.", 401)
    row = query_db(
        "SELECT id, username, email, role, created_at FROM users WHERE id = ?",
        (user_id,), one=True,
    )
    if row is None:
        session.clear()
        return error("User not found.", 404)
    return success(dict(row))
