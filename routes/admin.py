"""
Admin Dashboard routes.

Provides administrative endpoints for platform management under two blueprints:

- **admin_bp** (``/api/v1/admin``): Primary admin endpoints — dashboard stats,
  user listing, role changes, and user deletion.
- **admin_public_bp** (``/api/admin``): Public-facing alias for the ``set-role``
  endpoint (required by the frontend task spec).

Every endpoint verifies admin privileges by looking up the user's role in the
DB via ``_is_admin()`` — the JWT role claim is never trusted directly.
"""

import random
import datetime
import json
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from models.exchange_history import ExchangeHistory
from models.logs import PredictionLog, RecommendationLog
from extensions import db
from services.core import response_builder as resp
from sqlalchemy import desc

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")
admin_public_bp = Blueprint("admin_public", __name__, url_prefix="/api/admin")


def _is_admin():
    """Check whether the currently authenticated user has the admin role.

    Reads the user ID from the JWT identity, looks up the user in the DB,
    and returns True only if their role is ``"admin"``.

    Returns:
        bool: True if the current user is an admin, False otherwise.
    """
    raw = get_jwt_identity()
    identity = json.loads(raw) if isinstance(raw, str) else raw
    user_id = identity.get("id")
    if not user_id:
        return False
    user = User.query.get(user_id)
    return bool(user and user.role == "admin")


# ── GET /api/v1/admin/stats ─────────────────────────────────────────────────

@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    """Aggregate dashboard statistics for the admin panel.

    Returns:
        - Total and premium user counts.
        - Today's prediction and recommendation counts (from log tables).
        - 7-day price trends for USD, EUR, and Gold (from exchange_history).

    Returns:
        200: Stats object on success.
        403: Non-admin user.
    """
    if not _is_admin():
        return jsonify(resp.error("Admin access required.")), 403

    total_users = User.query.count()
    premium_users = User.query.filter_by(role="premium").count()
    
    # Count AI usage since midnight UTC for the "today" metrics
    start_of_day = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    predictions_today = PredictionLog.query.filter(PredictionLog.timestamp >= start_of_day).count()
    recommendations_today = RecommendationLog.query.filter(RecommendationLog.timestamp >= start_of_day).count()

    # USD Trend — last 7 days of exchange history
    usd_records = ExchangeHistory.query.filter_by(currency="USD").order_by(desc(ExchangeHistory.date)).limit(7).all()
    usd_trend = [{"date": str(r.date), "price": r.rate} for r in reversed(usd_records)]
    
    # EUR Trend
    eur_records = ExchangeHistory.query.filter_by(currency="EUR").order_by(desc(ExchangeHistory.date)).limit(7).all()
    eur_trend = [{"date": str(r.date), "price": r.rate} for r in reversed(eur_records)]
    
    # Gold Trend
    gold_records = ExchangeHistory.query.filter_by(currency="GOLD").order_by(desc(ExchangeHistory.date)).limit(7).all()
    gold_trend = [{"date": str(r.date), "price": r.rate} for r in reversed(gold_records)]
        
    return jsonify({
        "status": "success",
        "total_users": total_users,
        "premium_users": premium_users,
        "predictions_today": predictions_today,
        "recommendations_today": recommendations_today,
        "trends": {
            "usd": usd_trend,
            "eur": eur_trend,
            "gold": gold_trend
        }
    }), 200


# ── GET /api/v1/admin/users ─────────────────────────────────────────────────

@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def get_users():
    """List all registered users.

    Returns:
        200: Array of user dicts (via ``to_dict()``, passwords excluded).
        403: Non-admin user.
    """
    if not _is_admin():
        return jsonify(resp.error("Admin access required.")), 403
        
    users = User.query.all()
    return jsonify({
        "status": "success",
        "data": [u.to_dict() for u in users]
    }), 200


# ── PATCH /api/v1/admin/users/<id>/role ──────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@jwt_required()
def update_user_role(user_id):
    """Change a user's role (free / premium / admin).

    Also synchronises the ``plan`` field and clears ``subscription_expires``
    when downgrading away from premium.

    JSON Body:
        role (str): One of ``"free"``, ``"premium"``, ``"admin"``.

    Returns:
        200: Updated user dict.
        400: Missing or invalid role.
        403: Non-admin caller.
        404: User not found.
    """
    if not _is_admin():
        return jsonify(resp.error("Admin access required.")), 403
        
    data = request.get_json(silent=True)
    if not data or "role" not in data:
        return jsonify(resp.error("Missing role.")), 400
        
    new_role = data.get("role")
    if new_role not in ["free", "premium", "admin"]:
        return jsonify(resp.error("Invalid role.")), 400
        
    user = User.query.get(user_id)
    if not user:
        return jsonify(resp.error("User not found.")), 404
        
    user.role = new_role
    # Keep plan in sync: premium role → premium plan, free role → free plan
    user.plan = "premium" if new_role == "premium" else ("free" if new_role == "free" else user.plan)
    if new_role != "premium":
        user.subscription_expires = None
    db.session.commit()
    return jsonify(resp.success("Role updated.", user.to_dict())), 200


# ── DELETE /api/v1/admin/users/<id> ──────────────────────────────────────────

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    """Delete a user account.

    Safety check: the admin cannot delete their own account to prevent
    accidental lock-out.

    Returns:
        200: User deleted.
        400: Attempted self-deletion.
        403: Non-admin caller.
        404: User not found.
    """
    if not _is_admin():
        return jsonify(resp.error("Admin access required.")), 403
        
    user = User.query.get(user_id)
    if not user:
        return jsonify(resp.error("User not found.")), 404
        
    # Prevent the admin from dropping their own account
    raw = get_jwt_identity()
    identity = json.loads(raw) if isinstance(raw, str) else raw
    current_user_id = identity.get("id")
    if current_user_id == user_id:
        return jsonify(resp.error("Cannot drop your own admin account.")), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify(resp.success("User dropped successfully.")), 200


# ── POST /api/v1/admin/set-role ──────────────────────────────────────────────

@admin_bp.route("/set-role", methods=["POST"])
@jwt_required()
def set_role():
    """Bonus endpoint: set user role by user_id.

    Accepts a JSON body with ``user_id`` and ``role`` and applies the
    same role/plan sync logic as ``update_user_role``.

    JSON Body:
        user_id (int): Target user's ID.
        role (str): ``"free"``, ``"premium"``, or ``"admin"``.

    Returns:
        200: Updated user dict.
        400: Missing user_id or invalid role.
        403: Non-admin caller.
        404: User not found.
    """
    if not _is_admin():
        return jsonify(resp.error("Admin access required.")), 403

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    new_role = (data.get("role") or "").strip().lower()

    if not user_id:
        return jsonify(resp.error("Missing user_id.")), 400
    if new_role not in ["free", "premium", "admin"]:
        return jsonify(resp.error("Invalid role.")), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify(resp.error("User not found.")), 404

    user.role = new_role
    user.plan = "premium" if new_role == "premium" else ("free" if new_role == "free" else user.plan)
    if new_role != "premium":
        user.subscription_expires = None
    db.session.commit()

    return jsonify(resp.success("Role updated.", user.to_dict())), 200


# ── POST /api/admin/set-role (public alias) ──────────────────────────────────

@admin_public_bp.route("/set-role", methods=["POST"])
@jwt_required()
def set_role_public():
    """Alias endpoint requested in task: POST /api/admin/set-role.

    Delegates to the primary ``set_role()`` handler to avoid code duplication.
    """
    return set_role()
