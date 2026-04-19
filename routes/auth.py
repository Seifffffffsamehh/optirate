"""Authentication routes: Register, Login, Protected."""

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

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
VALID_ROLES = {"free", "premium", "admin"}


def _validate_register_payload(data: dict):
    """Return an error string or None if valid."""
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
    """Create a new user account."""
    data = request.get_json(silent=True)
    error = _validate_register_payload(data)
    if error:
        return jsonify({"error": error}), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()
    password = data["password"]
    role = data.get("role", "free").strip().lower()

    if role not in VALID_ROLES:
        return jsonify({"error": f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}"}), 400

    # Check uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    user = User(username=username, email=email, password=hashed_pw, role=role)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully.", "user": user.to_dict()}), 201


# ── Login ────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate and return a JWT."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "Username/email and password are required."}), 400

    # Allow login via username OR email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials."}), 401

    # Embed user metadata in the JWT identity
    identity = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }
    access_token = create_access_token(identity=identity)

    return jsonify({
        "message": "Login successful.",
        "access_token": access_token,
        "user": user.to_dict(),
    }), 200


# ── Protected ────────────────────────────────────────────────────────────────

protected_bp = Blueprint("protected", __name__, url_prefix="/api")


@protected_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    """Return the current authenticated user's data."""
    raw_identity = get_jwt_identity()
    # Identity is stored as JSON string; parse it back
    try:
        current_user = json.loads(raw_identity)
    except (json.JSONDecodeError, TypeError):
        current_user = raw_identity
    return jsonify({"message": "Access granted.", "user": current_user}), 200

