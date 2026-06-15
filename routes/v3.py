"""
V3 API routes — Historical Data Ingestion, AI Forecasting, and Premium Subscription.

This module provides premium-tier features behind the ``@premium_required``
decorator, as well as admin-only data-management endpoints.

Endpoints:
    POST /api/v3/upgrade                — Mock payment → 30-day premium upgrade
    POST /api/v3/ingest-history         — Admin: trigger CBE history ingestion
    GET  /api/v3/debug-history/<currency> — Admin: inspect stored history stats
    GET  /api/v3/predict/<currency>     — Premium: AI forecast via Prophet
    POST /api/v3/recommend              — Premium: strategic buy/sell recommendation

    - POST /api/v3/upgrade           : Upgrades free user to premium. Validates CVV and card lengths.
    - POST /api/v3/ingest-history   : Triggers a scraping sync from CBE. Restricted to Admin.
    - GET  /api/v3/debug-history/<c>: Returns coverage stats of historical rates. Restricted to Admin.
    - GET  /api/v3/predict/<currency>: Retrieves 14-day expected price forecast. Cached for 1 hour.
    - POST /api/v3/recommend         : Returns strategic recommendations (BUY/WAIT/SELL) based on forecast trends.
"""

import json
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from services.core import response_builder as resp
from services.engine.history_engine import sync_daily_history
from services.ai.ai_service import get_forecast_for_currency, get_strategic_recommendation
from services.cache.cache_manager import cache_manager
from models.exchange_history import ExchangeHistory
from models.user import User
from models.logs import PredictionLog, RecommendationLog
from extensions import db

v3_bp = Blueprint("v3", __name__, url_prefix="/api/v3")


# ── Internal helpers ─────────────────────────────────────────────────────────

def _get_role() -> str:
    """Read role from DB (JWT role is not trusted).

    Returns:
        str: ``"free"``, ``"premium"``, or ``"admin"``.  Defaults to ``"free"``
             if the user cannot be resolved.
    """
    try:
        uid = _get_user_id()
        if not uid:
            return "free"
        user = User.query.get(uid)
        if user:
            print(f"[ROLE CHECK] DB role = {user.role}")
        return user.role if user else "free"
    except Exception:
        return "free"


def _get_user_id() -> int | None:
    """Extract user ID from JWT identity.

    Returns:
        int | None: The numeric user ID, or None if extraction fails.
    """
    try:
        raw = get_jwt_identity()
        identity = json.loads(raw) if isinstance(raw, str) else raw
        return identity.get("id")
    except Exception:
        return None


def _check_and_downgrade_expired(user):
    """Auto-downgrade: if subscription has expired, revert plan to 'free'.

    This is called eagerly before granting premium access so that no expired
    user can slip through.

    Args:
        user: The User model instance to check.

    Returns:
        bool: True if the user was downgraded, False otherwise.
    """
    if user and user.plan == "premium" and user.subscription_expires:
        if datetime.utcnow() > user.subscription_expires:
            user.plan = "free"
            user.role = "free"
            user.subscription_expires = None
            db.session.commit()
            current_app.logger.info(
                "Auto-downgraded user %s — subscription expired.", user.username,
            )
            return True
    return False


# ── Premium access decorator ────────────────────────────────────────────────

def premium_required(f):
    """Decorator: rejects free-tier users from premium-only endpoints.

    Workflow:
        1. Extract user ID from the JWT.
        2. Look up the user in the DB (source of truth for role).
        3. Auto-downgrade if subscription has expired.
        4. Allow access only if role is ``"premium"`` or ``"admin"``.

    Returns 403 with an upgrade prompt if the user is on the free plan.
    Must be applied **after** ``@jwt_required()`` so the identity is available.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = _get_user_id()
        if uid:
            user = User.query.get(uid)
            if user:
                _check_and_downgrade_expired(user)
                if user.role in ("premium", "admin"):
                    return f(*args, **kwargs)
        return jsonify(resp.error(
            "This is a Premium feature. Please upgrade to gain access."
        )), 403
    return decorated


# ── POST /api/v3/upgrade ────────────────────────────────────────────────────

@v3_bp.route("/upgrade", methods=["POST"])
@jwt_required()
def upgrade_to_premium():
    """
    Mock payment endpoint — upgrades user to Premium for 30 days.

    SECURITY: This is a MOCK system. Card data is NOT stored or transmitted
    to any real gateway.  The card fields are validated for format only and
    then immediately discarded.

    JSON Body (required):
        card_number (str): Exactly 16 digits.
        name (str): Cardholder name.
        expiry (str): Card expiry date (not validated beyond presence).
        cvv (str): 3 or 4 digits.

    On success the user's plan/role are set to ``"premium"`` with a 30-day
    expiry, and a fresh JWT is issued containing the updated role.

    Returns:
        200: Upgrade successful with new access token and expiry date.
        400: Already premium, missing fields, or invalid card format.
        401: Invalid session.
        404: User not found.
    """
    uid = _get_user_id()
    if not uid:
        return jsonify(resp.error("Invalid session.")), 401

    user = User.query.get(uid)
    if not user:
        return jsonify(resp.error("User not found.")), 404

    # Check if already premium and not expired
    if user.plan == "premium" and user.subscription_expires:
        if datetime.utcnow() < user.subscription_expires:
            return jsonify(resp.error("You are already a Premium member.")), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify(resp.error("Request body must be JSON.")), 400

    card_number = (data.get("card_number") or "").strip()
    name = (data.get("name") or "").strip()
    expiry = (data.get("expiry") or "").strip()
    cvv = (data.get("cvv") or "").strip()

    # Validate all fields present
    if not all([card_number, name, expiry, cvv]):
        return jsonify(resp.error("All payment fields are required: card_number, name, expiry, cvv.")), 400

    # Mock validation: card_number must be exactly 16 digits
    if not re.match(r"^\d{16}$", card_number):
        return jsonify(resp.error("Card number must be exactly 16 digits.")), 400

    # CVV must be 3-4 digits
    if not re.match(r"^\d{3,4}$", cvv):
        return jsonify(resp.error("CVV must be 3 or 4 digits.")), 400

    # SECURITY: Card data is immediately discarded — never stored.
    # card_number, cvv, expiry are NOT persisted anywhere.
    del card_number, cvv, expiry

    # Business logic: upgrade user
    now = datetime.utcnow()
    user.plan = "premium"
    user.role = "premium"
    user.subscription_expires = now + timedelta(days=30)
    db.session.commit()

    current_app.logger.info(
        "User %s upgraded to Premium (expires %s).",
        user.username, user.subscription_expires.isoformat(),
    )

    # Issue a fresh JWT so the client immediately sees the updated role
    new_identity = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "plan": user.plan,
    }
    new_access_token = create_access_token(identity=new_identity)

    return jsonify(resp.success(
        "Congratulations! You are now a Premium member.",
        {
            "plan": user.plan,
            "role": user.role,
            "subscription_expires": user.subscription_expires.isoformat(),
            "access_token": new_access_token,
        }
    )), 200



@v3_bp.route("/ingest-history", methods=["POST"])
@jwt_required()
def ingest_history():
    """
    Trigger ingestion of historical data from CBE.

    Admin only.  Manually kicks off the same sync that APScheduler runs
    daily, useful for backfilling data or recovering after outages.

    Returns:
        200: Ingestion result summary.
        403: Non-admin user.
        500: Ingestion engine failure.
    """
    role = _get_role()
    if role != "admin":
        return jsonify(resp.error("Admin access required.")), 403

    try:
        result = sync_daily_history(current_app)
        if "error" in result:
            return jsonify(resp.error(result["message"])), 500
        
        return jsonify(resp.success(
            "Historical data ingestion complete.",
            result
        )), 200
    except Exception as e:
        return jsonify(resp.error(f"Ingestion failed: {str(e)}")), 500


# ── GET /api/v3/debug-history/<currency> ────────────────────────────────────

@v3_bp.route("/debug-history/<currency>", methods=["GET"])
@jwt_required()
def debug_history(currency):
    """
    Debug route returning data duration info.

    Admin only.  Returns the total number of distinct days stored, the
    earliest date, and the latest date for a given currency — useful for
    verifying that the daily sync is populating data correctly.

    Returns:
        200: Debug info (total_days, start_date, end_date).
        403: Non-admin user.
        500: Query failure.
    """
    role = _get_role()
    if role != "admin":
        return jsonify(resp.error("Admin access required.")), 403

    code = currency.upper()
    try:
        records = ExchangeHistory.query.filter_by(currency=code).order_by(ExchangeHistory.date.asc()).all()
        
        if not records:
            return jsonify(resp.success("No data found.", {"total_days": 0})), 200
            
        start_date = records[0].date
        end_date = records[-1].date
        
        # Calculate distinct days present
        total_days = len(set(r.date for r in records))
        
        return jsonify(resp.success(
            f"History debug for {code}",
            {
                "currency": code,
                "total_days": total_days,
                "start_date": str(start_date),
                "end_date": str(end_date)
            }
        )), 200
    except Exception as e:
        return jsonify(resp.error(f"Debug check failed: {str(e)}")), 500


# ── GET /api/v3/predict/<currency> ──────────────────────────────────────────

@v3_bp.route("/predict/<currency>", methods=["GET"])
@jwt_required()
@premium_required
def predict_currency(currency):
    """
    Generate AI predictions for future exchange rates.

    Uses Facebook Prophet trained on historical CBE data.  Results are cached
    for 1 hour (keyed by currency + role) to avoid redundant computation.
    Pass ``?refresh=true`` to force a fresh forecast.

    Each call (cached or fresh) is logged to ``PredictionLog`` for analytics.

    URL params:
        currency: ISO code (e.g. USD, EUR).

    Query params:
        refresh (bool, default false): Bypass the cache and regenerate.

    Returns:
        200: ``{predictions, model, timestamp, version}``
        404: Insufficient historical data for forecasting.
        500: Prophet or engine failure.
    """
    role = _get_role()
    code = currency.upper()
    
    # 1-hour cache logic — avoids re-running Prophet on every request
    cache_manager.set_ttl("pred", 3600) 
    cache_key = f"pred_{code}_{role}"
    
    force_refresh = request.args.get("refresh", "false").lower() == "true"
    
    if force_refresh:
        cache_manager.clear(cache_key)
    
    if not force_refresh:
        cached = cache_manager.get(cache_key)
        if cached is not None:
            db.session.add(PredictionLog(currency=code))
            db.session.commit()
            return jsonify(resp.success(
                f"Forecasting fetched from cache for {code}.",
                cached
            )), 200
        
    try:
        forecast_data = get_forecast_for_currency(code, role)
        
        if "message" in forecast_data and not forecast_data.get("predictions"):
             return jsonify(resp.error(forecast_data["message"])), 404
             
        # Format the response clearly
        formatted_data = {
            "predictions": forecast_data["predictions"],
            "model": forecast_data["model"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.1"
        }
        
        # Store in cache
        cache_manager.set(cache_key, formatted_data, domain="pred")
        
        db.session.add(PredictionLog(currency=code))
        db.session.commit()
        
        return jsonify(resp.success(
            f"AI Forecast generated for {code}.",
            formatted_data
        )), 200
        
    except Exception as e:
        return jsonify(resp.error(f"Prediction failed: {str(e)}")), 500


# ── POST /api/v3/recommend ──────────────────────────────────────────────────

@v3_bp.route("/recommend", methods=["POST"])
@jwt_required()
@premium_required
def recommend_action():
    """
    Generate strategic buy/sell recommendations based on forecasted data.

    Combines Prophet predictions with the AI service to advise whether the
    user should buy or sell a given amount of foreign currency.

    JSON Payload:
        currency (str): ISO code (e.g. "USD").
        amount (float): Amount of currency in question (must be > 0).
        action (str): ``"buy"`` or ``"sell"``.

    Role enforcement:
        Free users are restricted to USD and EUR only (though this endpoint
        also requires ``@premium_required``, so free users are blocked earlier).

    Query params:
        refresh (bool, default false): Force fresh forecast data.

    Each successful call is logged to ``RecommendationLog`` for analytics.

    Returns:
        200: Recommendation object from the AI service.
        400: Missing/invalid fields, or AI service returned an error.
        403: Free user or non-premium role.
        500: AI service failure.
    """
    role = _get_role()
    data = request.get_json()
    
    if not data:
        return jsonify(resp.error("Missing JSON payload.")), 400
        
    currency = data.get("currency")
    amount = data.get("amount")
    action = data.get("action")
    
    if not all([currency, amount, action]):
        return jsonify(resp.error("Missing required fields: currency, amount, action.")), 400
        
    code = currency.upper()
    action = action.lower()
    
    # Role Enforcement
    if role == "free" and code not in ["USD", "EUR"]:
        return jsonify(resp.error("Free users are restricted to USD and EUR.")), 403
        
    if action not in ["buy", "sell"]:
        return jsonify(resp.error("Action must be 'buy' or 'sell'.")), 400
        
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return jsonify(resp.error("Amount must be a positive number.")), 400
        
    force_refresh = request.args.get("refresh", "false").lower() == "true"
        
    try:
        recommendation = get_strategic_recommendation(code, amount, action, role, force_refresh)
        
        if "error" in recommendation:
            return jsonify(resp.error(recommendation["error"])), 400
            
        db.session.add(RecommendationLog(currency=code, action=action))
        db.session.commit()
            
        return jsonify(resp.success(
            f"Strategic recommendation generated for {code}.",
            recommendation
        )), 200
        
    except Exception as e:
        return jsonify(resp.error(f"Recommendation generation failed: {str(e)}")), 500
