"""Health-check route."""

from flask import Blueprint, jsonify
from sqlalchemy import text
from extensions import db

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Return service and database status."""
    db_status = "disconnected"
    try:
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    status_code = 200 if db_status == "connected" else 503
    return jsonify({"status": "ok", "database": db_status}), status_code
