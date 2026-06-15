"""
Health-check route.

Provides a lightweight ``GET /api/health`` endpoint for load balancers,
container orchestrators, and uptime monitors to verify that both the Flask
process and the database connection are operational.
"""

from flask import Blueprint, jsonify
from sqlalchemy import text
from extensions import db

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Return service and database status.

    Executes a trivial ``SELECT 1`` query to verify the database is
    reachable.  Returns 200 if connected, 503 if the DB is unreachable.

    Returns:
        200: Service healthy, DB connected.
        503: Database unreachable — alerts the monitoring system.
    """
    db_status = "disconnected"
    try:
        # Lightweight query that succeeds as long as the DB connection is alive
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    if db_status == "connected":
        return jsonify({
            "status": "success",
            "message": "Service is healthy.",
            "data": {"database": db_status},
        }), 200

    return jsonify({
        "status": "error",
        "message": "Database is unreachable.",
    }), 503
