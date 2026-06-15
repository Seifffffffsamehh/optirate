"""
V2 API routes — Financial Data Engine endpoints.

All endpoints live under ``/api/v2`` and provide real-time and historical
financial data (currencies, gold, silver, news).  Most routes require a valid
JWT; the user's role (read from the DB, never trusted from the token) determines
which currencies or assets they can access.

Endpoints:
    GET /api/v2/currencies       — Exchange rates from Egyptian banks
    GET /api/v2/gold             — Gold prices in Egypt
    GET /api/v2/silver           — Silver prices in Egypt
    GET /api/v2/history/<currency> — Historical exchange rates for a currency
    GET /api/v2/news             — Latest economic news (public, no JWT)
    GET /api/v2/metals/history   — Intraday / weekly metal price history
"""

import json
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User

from services.engine.currency_engine import (
    get_currency_rates,
    get_average_currency_rates,
    REQUIRED_CURRENCIES,
)
from services.engine.gold_engine import get_gold_prices
from services.engine.silver_engine import get_silver_prices
from services.engine.history_engine import get_history
from services.engine.news_engine import get_latest_news
from services.core import response_builder as resp

v2_bp = Blueprint("v2", __name__, url_prefix="/api/v2")


def _get_current_user():
    """Resolve current user from JWT identity, with DB as source of truth.

    Parses the JSON-encoded JWT "sub" claim, extracts the user ID, and
    performs a DB lookup.

    Returns:
        User | None: The SQLAlchemy User instance, or None on any failure.
    """
    try:
        raw = get_jwt_identity()
        identity = json.loads(raw) if isinstance(raw, str) else raw
        user_id = identity.get("id")
        if not user_id:
            return None
        return User.query.get(user_id)
    except Exception:
        return None


def _get_role() -> str:
    """Read role from DB (never trust role claim in JWT).

    Returns:
        str: The user's current role (``"free"``, ``"premium"``, or ``"admin"``).
             Defaults to ``"free"`` if the user cannot be resolved.
    """
    user = _get_current_user()
    if user:
        print(f"[ROLE CHECK] DB role = {user.role}")
    return user.role if user else "free"


# ── GET /api/v2/currencies ───────────────────────────────────────────────────

@v2_bp.route("/currencies", methods=["GET"])
@jwt_required()
def currencies():
    """
    Get exchange rates from Egyptian banks.

    Query params:
        currency (optional): Filter by specific currency code (e.g., USD).
        mode (optional): "banks" (default) or "average" (on-the-fly averages).

    Role filtering:
        free  → USD, EUR, SAR, AED, GBP
        premium/admin → all 11 currencies

    Returns:
        200: List of rate objects with count metadata.
        500: Upstream scraping/engine failure.
    """
    role = _get_role()
    currency_code = request.args.get("currency", None)
    mode = (request.args.get("mode", "banks") or "banks").strip().lower()

    try:
        if mode == "average":
            rates = get_average_currency_rates(currency_code=currency_code, role=role)

            # Debug visibility to prove real rows are used for each average.
            for item in rates:
                print(
                    "Banks used for AVG calculation:",
                    item.get("currency"),
                    item.get("banks_used", []),
                )
        else:
            rates = get_currency_rates(currency_code=currency_code, role=role)
    except Exception:
        return jsonify(resp.error("Failed to fetch currency data.")), 500

    return jsonify(resp.success(
        (
            f"Fetched {len(rates)} exchange-rate averages."
            if mode == "average"
            else f"Fetched {len(rates)} exchange rates."
        ),
        rates,
        count=len(rates),
    )), 200


# ── GET /api/v2/gold ─────────────────────────────────────────────────────────

@v2_bp.route("/gold", methods=["GET"])
@jwt_required()
def gold():
    """
    Get gold prices in Egypt.

    Returns the full list of gold karat prices for all users.  The frontend
    applies visual gating (blurring) for free-tier users — the backend sends
    all data regardless of role.

    Returns:
        200: List of gold price objects with count.
        500: Upstream engine failure.
    """
    role = _get_role()

    try:
        prices = get_gold_prices(role=role)
    except Exception:
        return jsonify(resp.error("Failed to fetch gold data.")), 500

    return jsonify(resp.success(
        f"Fetched {len(prices)} gold price(s).",
        prices,
        count=len(prices),
    )), 200


# ── GET /api/v2/silver ───────────────────────────────────────────────────────

@v2_bp.route("/silver", methods=["GET"])
@jwt_required()
def silver():
    """Get silver prices in Egypt.

    Returns:
        200: Silver price data.
        500: Upstream engine failure.
    """
    try:
        prices = get_silver_prices()
    except Exception:
        return jsonify(resp.error("Failed to fetch silver data.")), 500

    return jsonify(resp.success("Fetched silver prices.", prices)), 200


# ── GET /api/v2/history/<currency> ───────────────────────────────────────────

@v2_bp.route("/history/<currency>", methods=["GET"])
@jwt_required()
def history(currency):
    """
    Get historical exchange rates for a specific currency.

    URL params:
        currency: ISO currency code (e.g., USD, EUR).

    Query params:
        limit (optional): Max records to return (default 90, clamped 1–365).

    Returns:
        200: List of historical rate records with count.
        400: Unsupported currency code.
        500: History engine failure.
    """
    code = currency.upper()
    if code not in REQUIRED_CURRENCIES:
        return jsonify(resp.error(
            f"Unsupported currency: {code}. Supported: {', '.join(REQUIRED_CURRENCIES)}"
        )), 400

    try:
        limit = int(request.args.get("limit", 90))
        # Clamp between 1 and 365 to prevent excessive queries
        limit = min(max(limit, 1), 365)
    except (ValueError, TypeError):
        limit = 90

    try:
        records = get_history(code, limit=limit)
    except Exception:
        return jsonify(resp.error(f"Failed to fetch history for {code}.")), 500

    return jsonify(resp.success(
        f"Fetched {len(records)} historical records for {code}.",
        records,
        count=len(records),
    )), 200

# ── GET /api/v2/news ─────────────────────────────────────────────────────────

@v2_bp.route("/news", methods=["GET"])
def get_news():
    """
    Public endpoint: Fetch latest economic news.

    The news engine tries sources in priority order: NewsAPI → Google RSS → Static fallback.
    No JWT required — this endpoint is publicly accessible.

    Query params:
        limit (int, default 5): Number of articles to return.
        keyword (str, default ""): Filter articles by keyword.

    Returns:
        200: List of news articles.
        500: All news sources failed.
    """
    try:
        limit = request.args.get("limit", default=5, type=int)
        keyword = request.args.get("keyword", default="")
        news_result = get_latest_news(limit=limit, keyword=keyword)
        
        return jsonify(resp.success(
            "Latest news retrieved.",
            news_result["data"]
        )), 200
    except Exception as e:
        return jsonify(resp.error(f"Failed to fetch news: {e}")), 500

# ── GET /api/v2/metals/history ───────────────────────────────────────────────

@v2_bp.route("/metals/history", methods=["GET"])
@jwt_required()
def metals_history():
    """
    Get historical data for a specific metal asset.

    Acts as an Intraday Tracker: returns up to 7 days of stored history plus
    a live data point from the current scraper run.  The ``type`` field in
    each record distinguishes ``"historical"`` from ``"live"`` entries.

    Query params:
        asset (str, default "ذهب عيار 21"): Arabic or English asset name.

    Returns:
        200: List of price points (historical + live) for the requested asset.
    """
    asset = request.args.get("asset", "ذهب عيار 21")
    
    current_price = None
    # Determine whether the requested asset is gold or silver based on name
    is_gold = "ذهب" in asset or "Gold" in asset or "أوقية" in asset
    
    try:
        from services.engine.gold_engine import get_gold_prices
        from services.engine.silver_engine import get_silver_prices
        
        if is_gold:
            prices = get_gold_prices(role=_get_role())
            # Match the karat label in the asset name to find the current price
            for p in prices:
                k = str(p.get("karat", ""))
                if k in asset or (k == "Coin" and "الجنيه" in asset) or (k == "Ounce USD" and "USD" in asset):
                    current_price = p.get("sell", None)
                    break
        else:
            prices = get_silver_prices()
            if prices:
                current_price = prices[0].get("sell", None)
    except Exception:
        pass
        
    from models.exchange_history import ExchangeHistory
    # Map the asset type to a canonical code stored in exchange_history
    code = "GOLD" if is_gold else "SILVER"
    
    # Try fetching accumulated history
    records = ExchangeHistory.query.filter_by(currency=code).order_by(ExchangeHistory.date.desc()).limit(7).all()
    
    history = []
    if records:
        for r in records:
            history.append({
                "date": str(r.date),
                "price": r.rate,
                "type": "historical"
            })
        history.reverse()
        
    # Append the live intraday point
    import datetime
    now = datetime.datetime.now()
    if current_price:
        history.append({
            "date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "price": current_price,
            "type": "live"
        })
        
    return jsonify(resp.success(
        f"Fetched history for {asset}",
        history
    )), 200
