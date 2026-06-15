"""
Authentication routes: Register, Login, Protected.

This module exposes two blueprints:

- **auth_bp** (``/api/auth``): Registration, login, profile management, logout.
- **protected_bp** (``/api``): JWT-protected endpoints that return the
  current user's data (``/protected``, ``/me``).

Authentication Flow:
    1. User posts credentials to `/api/auth/register` (creates account) or `/api/auth/login`.
    2. `/api/auth/login` verifies credentials against DB records, generates a bcrypt-based match, 
       and builds a JWT access token using `flask_jwt_extended`.
    3. The client receives the JWT token and attaches it as `Authorization: Bearer <token>` in the header
       for all subsequent authenticated API requests.

JWT Identity Structure:
    The JWT "sub" claim carries a JSON-encoded dict with keys:
    ``{"id": int, "username": str, "role": str, "plan": str}``
    Every handler that needs the current user must parse this back to a dict.
"""

import re
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from extensions import db, bcrypt
from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ── Helpers ──────────────────────────────────────────────────────────────────

# Simple email regex — not RFC 5322-complete, but sufficient for basic validation
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Whitelist of roles that can be assigned during registration
VALID_ROLES = {"free", "premium", "admin"}


def _validate_register_payload(data: dict):
    """Validate the registration request body.

    Checks for required fields, username length (3–80 chars), email format,
    and minimum password length (6 chars).

    Args:
        data: Parsed JSON body from the request.

    Returns:
        An error message string if validation fails, or ``None`` if valid.
    """
    if not data:
        return "Request body must be JSON."

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return "Fields 'username', 'email', and 'password' are required."

    if len(username) < 3 or len(username) > 80:
        return "Username must be between 3 and 80 characters."

    if not _EMAIL_RE.match(email):
        return "Invalid email format."

    if len(password) < 6:
        return "Password must be at least 6 characters."

    return None


# ── Register ─────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    """Create a new user account.

    Expects JSON: ``{"username", "email", "password", "role?" (default "free")}``.
    Validates input, checks uniqueness of username and email, hashes the
    password with bcrypt, and persists the new user.

    Returns:
        201: User created successfully with ``user.to_dict()`` in data.
        400: Validation error or duplicate username/email.
    """
    data = request.get_json(silent=True)
    error = _validate_register_payload(data)
    if error:
        return jsonify({"status": "error", "message": error}), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()
    password = data["password"]
    role = data.get("role", "free").strip().lower()

    if role not in VALID_ROLES:
        return jsonify({
            "status": "error",
            "message": f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        }), 400

    # Check uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({"status": "error", "message": "Username already taken."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered."}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    user = User(username=username, email=email, password=hashed_pw, role=role)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "User registered successfully.",
        "data": user.to_dict(),
    }), 201


# ── Login ────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate and return a JWT.

    Accepts either ``username`` or ``email`` as the identifier.  On success,
    returns a JWT access token whose "sub" claim contains a JSON-encoded dict
    of user metadata (id, username, role, plan).

    Expects JSON: ``{"username" or "email", "password"}``.

    Returns:
        200: Login successful with ``access_token`` and ``user`` dict.
        400: Missing required fields.
        401: Invalid credentials.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Request body must be JSON."}), 400

    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"status": "error", "message": "Username/email and password are required."}), 400

    # Allow login via username OR email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"status": "error", "message": "Invalid credentials."}), 401

    # Embed user metadata in the JWT identity (id, username, role, plan)
    identity = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "plan": user.plan if hasattr(user, 'plan') else user.role,
    }
    access_token = create_access_token(identity=identity)

    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "data": {
            "access_token": access_token,
            "user": user.to_dict(),
        },
    }), 200


# ── Protected ────────────────────────────────────────────────────────────────

protected_bp = Blueprint("protected", __name__, url_prefix="/api")


@protected_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    """Return the current authenticated user's data.

    Parses the JWT identity (JSON string) back into a dict, looks up the user
    in the DB, and returns their full profile via ``to_dict()``.

    Returns:
        200: User data on success; falls back to raw identity if DB lookup fails.
    """
    raw_identity = get_jwt_identity()
    # Identity is stored as JSON string; parse it back
    try:
        current_user = json.loads(raw_identity)
    except (json.JSONDecodeError, TypeError):
        current_user = raw_identity

    user = None
    if isinstance(current_user, dict):
        user = User.query.get(current_user.get("id"))

    return jsonify({
        "status": "success",
        "message": "Access granted.",
        "data": user.to_dict() if user else current_user,
    }), 200


@protected_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Authoritative current user endpoint (DB is source of truth).

    Unlike ``/protected``, this endpoint returns only core identity fields
    (id, username, role) and always reads from the database — ensuring the
    role reflects any recent changes (e.g. subscription downgrades).

    Returns:
        200: ``{id, username, role}`` from the database.
        401: Invalid session (no user ID in token).
        404: User record not found in DB.
    """
    raw_identity = get_jwt_identity()
    try:
        identity = json.loads(raw_identity) if isinstance(raw_identity, str) else raw_identity
    except (json.JSONDecodeError, TypeError):
        identity = raw_identity

    user_id = identity.get("id") if isinstance(identity, dict) else None
    if not user_id:
        return jsonify({"status": "error", "message": "Invalid session."}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 404
    print(f"[ROLE CHECK] DB role = {user.role}")

    return jsonify({
        "status": "success",
        "data": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        },
    }), 200


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Retrieve the full profile of the currently authenticated user.

    Returns:
        200: Full user dict via ``to_dict()``.
        404: User not found in DB.
    """
    raw_identity = get_jwt_identity()
    try:
        current_user = json.loads(raw_identity) if isinstance(raw_identity, str) else raw_identity
    except (json.JSONDecodeError, TypeError):
        current_user = raw_identity

    user = User.query.get(current_user["id"])
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify({
        "status": "success",
        "data": user.to_dict(),
    }), 200


@auth_bp.route("/update-profile", methods=["PATCH", "POST"])
@jwt_required()
def update_profile():
    """Update the current user's profile (currently username only).

    Expects JSON: ``{"username": "new_name"}``.
    Validates length (3–80 chars) and uniqueness before persisting.

    Returns:
        200: Updated user dict.
        400: Validation error or duplicate username.
        404: User not found.
    """
    raw_identity = get_jwt_identity()
    try:
        current_user = json.loads(raw_identity) if isinstance(raw_identity, str) else raw_identity
    except (json.JSONDecodeError, TypeError):
        current_user = raw_identity

    user = User.query.get(current_user["id"])
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Request body must be JSON."}), 400

    new_username = (data.get("username") or "").strip()
    if new_username:
        if len(new_username) < 3 or len(new_username) > 80:
            return jsonify({"status": "error", "message": "Username must be between 3 and 80 characters."}), 400
        if new_username != user.username and User.query.filter_by(username=new_username).first():
            return jsonify({"status": "error", "message": "Username already taken."}), 400
        user.username = new_username
        db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Profile updated successfully.",
        "data": user.to_dict(),
    }), 200

@auth_bp.route("/logout", methods=["POST"])
@jwt_required(optional=True)
def logout():
    """Log the user out.

    Since JWTs are stateless, this endpoint simply returns a success
    response.  The client is responsible for discarding the token.
    JWT is optional so even unauthenticated calls don't error.

    Returns:
        200: Always succeeds.
    """
    return jsonify({
        "status": "success",
        "message": "Logged out successfully."
    }), 200
