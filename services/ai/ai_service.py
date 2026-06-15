"""
AI Service — orchestration layer for currency forecasting and strategic recommendations.

This module is the primary entry point for all AI-driven functionality in OptiRate.
It provides two main capabilities:

1. **Forecasting** (`get_forecast_for_currency`):
   Fetches historical exchange-rate data from the database, cleans and resamples it,
   then delegates to the Prophet model (or a pure-Python linear fallback when pandas
   is unavailable) to produce daily price predictions with confidence intervals.

2. **Strategic Recommendations** (`get_strategic_recommendation`):
   Consumes forecast output and live market data to generate actionable BUY / SELL /
   HOLD / WAIT signals.  The recommendation considers forecast trend direction,
   volatility (computed from recent DB records or live bank rates), confidence scores,
   and user intent (buying vs. selling) to produce human-readable advice together
   with risk / reward scenarios.

Dependencies:
    - models.exchange_history: ORM model for historical rate storage.
    - services.cache.cache_manager: TTL-based in-memory cache for forecast data.
    - services.engine.currency_engine: Live spot-rate retrieval from bank providers.
    - services.ai.prophet_model: Prophet-based forecasting (optional; gracefully
      degrades to a pure-Python fallback if pandas/prophet are not installed).
"""

import logging
from datetime import datetime, timedelta

from models.exchange_history import ExchangeHistory
from services.cache.cache_manager import cache_manager
from services.engine.currency_engine import get_live_spot_rate

# Prophet and pandas are optional heavyweight dependencies.
# When unavailable, the service falls back to a pure-Python linear model.
try:
    import pandas as pd
    from services.ai.prophet_model import generate_forecast
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure-Python Linear Fallback Forecast
# ---------------------------------------------------------------------------

def _pure_python_forecast(records, horizon_days: int, spot_rate: float = None) -> tuple[list[dict], str]:
    """
    Lightweight linear-trend forecast that requires no external ML libraries.

    This fallback is used when pandas/Prophet are not installed.  It performs
    ordinary-least-squares regression on the most recent 14 data points to
    capture the short-term trend direction, then projects forward from the
    current live spot rate (not the regression intercept) to avoid stale-data
    drift.

    Algorithm overview:
        1. Compute OLS slope on the last ≤14 records.
        2. Cap the slope at ±0.5% of the mean rate per day to prevent
           unrealistic extrapolation.
        3. Project forward day-by-day from the live spot rate.
        4. Hard-anchor Day 1 to the exact spot rate so the forecast starts
           at the current market price.
        5. Clamp each day's movement to ±3% of the previous day.
        6. Build 95% confidence bands (±1.96σ), further constrained to
           ±3% of the expected value and guaranteed non-degenerate width.

    Args:
        records:      List of ExchangeHistory ORM objects, ordered by date ASC.
        horizon_days: Number of future days to forecast.
        spot_rate:    Live market spot rate.  Falls back to the last DB rate
                      if not supplied or ≤0.

    Returns:
        A tuple of (predictions, model_name) where predictions is a list of
        dicts with keys: date, expected, lower, upper.
    """
    if not records:
        return [], "none"
        
    from datetime import date
    
    # Use only the most recent 14 records for regression so the model
    # captures recent market direction without dilution from older data.
    recent_records = records[-14:] if len(records) > 14 else records
    
    # Calculate slope on recent window
    x = list(range(len(recent_records)))
    y = [r.rate for r in recent_records]
    
    n = len(recent_records)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    # OLS slope: Σ((xi - x̄)(yi - ȳ)) / Σ((xi - x̄)²)
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denominator = sum((xi - mean_x) ** 2 for xi in x)
    
    slope = numerator / denominator if denominator != 0 else 0
    
    # Cap the slope to avoid extreme unrealistic predictions
    # Maximum allowed daily change is 0.5% of the mean rate
    max_daily_change = mean_y * 0.005
    if slope > max_daily_change:
        slope = max_daily_change
    elif slope < -max_daily_change:
        slope = -max_daily_change
        
    last_date = records[-1].date
    current_price = spot_rate if spot_rate and spot_rate > 0 else y[-1]
    
    # Std deviation from the recent window — used for confidence band width
    variance = sum((yi - mean_y)**2 for yi in y) / n
    std_dev = variance ** 0.5
    
    # KEY FIX: Project from the current spot rate using the slope for direction,
    # NOT from the regression line intercept. This avoids stale DB intercepts
    # pulling the forecast away from the live market level.
    predictions = []
    last_day_price = current_price
    
    for i in range(1, horizon_days + 1):
        target_date = last_date + timedelta(days=i)
        
        # Project from spot rate using the trend slope
        pred_y = current_price + slope * i
        
        # Hard anchor Day 1 to live spot rate
        if i == 1:
            pred_y = current_price
        
        # Apply daily movement constraints (±3% max per day)
        max_drop = last_day_price * 0.97
        max_spike = last_day_price * 1.03
        if pred_y < max_drop:
            pred_y = max_drop
        elif pred_y > max_spike:
            pred_y = max_spike
        
        # 95% confidence margin (z=1.96); fallback to 2% of price if no variance
        margin = 1.96 * std_dev if std_dev > 0 else (pred_y * 0.02)
        
        # Constrain bounds (±3% of expected) and guarantee non-zero width
        lower = pred_y - margin
        upper = pred_y + margin
        lower = max(lower, pred_y * 0.97)
        lower = min(lower, pred_y * 0.999)
        upper = min(upper, pred_y * 1.03)
        upper = max(upper, pred_y * 1.001)
        
        predictions.append({
            "date": target_date.strftime("%Y-%m-%d"),
            "expected": round(pred_y, 4),
            "lower": round(lower, 4),
            "upper": round(upper, 4)
        })
        
        last_day_price = pred_y
        
    return predictions, "pure_python_linear_fallback"


# ---------------------------------------------------------------------------
# Forecast Orchestrator
# ---------------------------------------------------------------------------

def get_forecast_for_currency(currency: str, role: str) -> dict:
    """
    Fetch historical exchange-rate data, clean it, and run the forecasting model.

    Pipeline:
        1. Query all historical records for the currency from the DB.
        2. If pandas is unavailable, delegate to the pure-Python linear fallback.
        3. Otherwise, build a DataFrame, resample to daily frequency (filling
           gaps via linear interpolation), and verify data freshness (≤48 h).
        4. Delegate to Prophet via ``generate_forecast()``.

    The forecast horizon is role-gated:
        - premium / admin users: 14-day horizon.
        - all other roles:       2-day horizon.

    Args:
        currency: ISO currency code (case-insensitive).
        role:     Authenticated user's subscription tier.

    Returns:
        Dict with keys: predictions (list[dict]), model (str),
        and optionally message (str) on failure.
    """
    code = currency.upper()
    
    # Allowed horizons:
    # Premium/admin get a 14-day forecast; free-tier users only 2 days.
    horizon_days = 14 if role in ("premium", "admin") else 2
    
    # 1. Fetch data from DB
    records = ExchangeHistory.query.filter_by(currency=code).order_by(ExchangeHistory.date.asc()).all()
    
    if not records:
        return {
            "predictions": [],
            "model": "none",
            "message": "No historical data available for this currency."
        }
    
    # When pandas is unavailable, use the lightweight pure-Python forecast
    if not HAS_PANDAS:
        spot_rate = get_live_spot_rate(code)
        predictions, model_name = _pure_python_forecast(records, horizon_days, spot_rate=spot_rate)
        return {
            "predictions": predictions,
            "model": model_name
        }
    
    # Convert ORM records into a Prophet-compatible DataFrame (ds, y)
    df = pd.DataFrame([{
        "ds": r.date,
        "y": r.rate
    } for r in records])
    
    # 2. Data Cleaning
    # Convert 'ds' to datetime
    df['ds'] = pd.to_datetime(df['ds'])
    
    # Verify DB freshness (<24h)
    # Reject predictions if the newest data point is older than 48 hours,
    # which accounts for weekends while still ensuring reasonable freshness.
    last_record_date = df['ds'].max()
    if (pd.Timestamp.now().tz_localize(None) - last_record_date.tz_localize(None)).total_seconds() > 86400 * 2:
        # Allowing up to 48 hours to account for weekends, but strictly reject > 2 days
        return {
            "predictions": [],
            "model": "none",
            "message": "Stale historical data. Prediction aborted."
        }
    
    # Set index for resampling
    df.set_index('ds', inplace=True)
    
    # Resample daily and interpolate linearly
    # This fills gaps (e.g. weekends / missing scrapes) with smooth values.
    df = df.resample('D').interpolate(method='linear')
    
    # Reset index for prophet model
    df.reset_index(inplace=True)
    
    # Drop any remaining NaNs
    df.dropna(subset=['y'], inplace=True)
    
    # 3. Forecast — delegate to Prophet (with live spot-rate anchor)
    spot_rate = get_live_spot_rate(code)
    predictions, model_name = generate_forecast(df, horizon_days, spot_rate=spot_rate)
    
    return {
        "predictions": predictions,
        "model": model_name
    }


# ---------------------------------------------------------------------------
# Strategic Recommendation Engine
# ---------------------------------------------------------------------------

def get_strategic_recommendation(currency: str, amount: float, action: str, role: str, force_refresh: bool = False) -> dict:
    """
    Evaluate forecast and market data to generate an actionable trading recommendation.

    This is the core decision engine that translates raw price forecasts into
    human-readable BUY / SELL / HOLD / WAIT signals.  The recommendation is
    tailored to the user's stated intent (buying vs. selling currency).

    Decision pipeline:
        1. Retrieve (or generate) a cached forecast for the currency.
        2. Derive expected price change (%) from current spot to end of horizon.
        3. Compute a **confidence score** from the final-day prediction interval
           width: narrower bands → higher confidence.
        4. Calculate **volatility** from the most recent 7 DB records (or live
           bank sell rates when DB data is stale >7 days). Volatility is
           classified as low (<0.5%), medium (0.5–1.5%), or high (>1.5%).
        5. Apply **volatility penalty**: high volatility reduces confidence by 20 pts.
        6. Run the **decision matrix** against thresholds:
           - BUY intent:  "BUY NOW" when expected rise ≥0.75%, vol ≠ high, confidence ≥65.
           - SELL intent:  "SELL NOW" when expected decline ≤ −1.0%;
                           "WAIT BEFORE SELLING" when rise ≥0.75% (to capture upside).
        7. Compute gain/loss scenarios (best-case and worst-case %).
        8. Classify market mood (Bullish/Bearish/Unstable/Stable), risk level,
           and recommendation strength (STRONG/MODERATE/WEAK SIGNAL).

    Args:
        currency:      ISO currency code (case-insensitive).
        amount:        Transaction amount (reserved for future position-size logic).
        action:        User intent — "buy" or "sell".
        role:          User subscription tier (affects forecast horizon).
        force_refresh: When True, bypasses the forecast cache.

    Returns:
        Dict containing: decision, decision_text, simple_summary, reason,
        best_day_to_act, confidence_score, volatility_level, market_mood,
        risk_level, recommendation_strength, metrics, and scenarios.
        Returns ``{"error": ...}`` on invalid input or missing data.
    """
    import math

    code = currency.upper()
    action = action.lower()

    if action not in ("buy", "sell"):
        return {"error": "Invalid action. Must be 'buy' or 'sell'."}

    # ── Fetch Forecast ──
    # Forecast predictions are cached for 1 hour to avoid redundant computation.
    cache_manager.set_ttl("pred", 3600)
    cache_key = f"pred_{code}_{role}"
    forecast_data = None if force_refresh else cache_manager.get(cache_key)
    
    if not forecast_data:
        forecast_data = get_forecast_for_currency(code, role)
        if forecast_data.get("predictions"):
            cache_manager.set(cache_key, forecast_data, domain="pred")
            
    predictions = forecast_data.get("predictions", [])
    if not predictions:
        return {"error": "No forecast available. Insufficient data to generate prediction."}
    
    # Day 1 is hard-anchored to the live spot rate during forecasting,
    # so predictions[0]["expected"] equals today's market price.
    current_price = predictions[0]["expected"]
    
    logger.info(f"[Validation] Recommendation Spot Rate for {code}: {current_price}")
    
    # We use the final predicted day to determine the overall trend
    final_day = predictions[-1]
    predicted_price = final_day["expected"]
    
    # Percentage change from today's price to end-of-horizon price
    # expected_change = (predicted_price - current_price) / current_price
    expected_change = (predicted_price - current_price) / current_price if current_price > 0 else 0
    expected_change_pct = expected_change * 100
    
    # ── Confidence Score ──────────────────────────────────────────────
    # Derived from the width of the final-day prediction interval relative
    # to the predicted value.  Narrower intervals → higher confidence.
    # Score is clamped to [0, 100].
    yhat = final_day["expected"]
    yhat_lower = final_day["lower"]
    yhat_upper = final_day["upper"]
    
    conf = (1 - (yhat_upper - yhat_lower) / yhat) * 100 if yhat > 0 else 0
    confidence_score = round(max(0, min(100, conf)), 0)
    
    # ── Volatility calculation ─────────────────────────────────────────
    # Use live bank rates for volatility when DB records are stale (>7 days)
    # to avoid inflated volatility from old data spikes.
    from datetime import date as _date
    db_records = ExchangeHistory.query.filter_by(currency=code).order_by(ExchangeHistory.date.desc()).limit(7).all()
    db_stale = True
    if db_records:
        days_since = (_date.today() - db_records[0].date).days
        db_stale = days_since > 7
    
    if db_stale:
        # Use live bank sell rates for volatility (more current)
        from services.engine.currency_engine import get_currency_rates
        live_banks = get_currency_rates(currency_code=code, role="premium")
        rates = [float(b.get("sell", 0)) for b in live_banks if b.get("sell")]
    else:
        # Filter out None and NaN values from recent DB records
        rates = [r.rate for r in db_records if r.rate is not None and not (isinstance(r.rate, float) and math.isnan(r.rate))]
    
    # Volatility classification using sample standard deviation:
    #   low:     < 0.5%  — stable market
    #   medium:  0.5–1.5% — normal fluctuation
    #   high:    > 1.5%  — elevated risk
    if len(rates) >= 2:
        mean_rate = sum(rates) / len(rates)
        variance = sum((r - mean_rate)**2 for r in rates) / (len(rates) - 1)
        std_dev = variance ** 0.5
        volatility_pct = (std_dev / mean_rate) * 100
        if volatility_pct < 0.5:
            vol_level = "low"
        elif volatility_pct <= 1.5:
            vol_level = "medium"
        else:
            vol_level = "high"
    else:
        vol_level = "unknown"
    
    # Volatility override — high volatility penalises confidence by 20 points
    if vol_level == "high":
        confidence_score = max(0, confidence_score - 20)

    # ── BUY / SELL DECISION LOGIC ──────────────────────────────────────
    # Decision thresholds:
    #   BUY NOW:             expected rise ≥ 0.75%, vol ≠ high, confidence ≥ 65
    #   WAIT (buy):          otherwise (price stable/dropping or uncertain)
    #   WAIT BEFORE SELLING: expected rise ≥ 0.75% (capture upside)
    #   SELL NOW:            expected decline ≤ −1.0%
    #   HOLD (sell):         flat/uncertain market
    decision = ""
    reason = ""
    simple_summary = ""
    
    if action == "buy":
        if expected_change_pct >= 0.75 and vol_level != "high" and confidence_score >= 65:
            decision = "BUY NOW"
            reason = f"The forecast suggests that {code} prices may rise significantly soon. Purchasing now could help you avoid paying higher exchange rates later."
            simple_summary = "Prices are expected to rise. Buy now."
        else:
            decision = "WAIT"
            if expected_change_pct < 0:
                reason = f"The forecast expects {code} prices to drop or remain stable. Waiting could give you a better purchasing rate."
            else:
                reason = f"The expected increase is small or volatility is high. Waiting provides a safer entry point."
            simple_summary = "Wait for a better rate or clearer trend."
            
    elif action == "sell":
        if expected_change_pct >= 0.75 and vol_level != "high" and confidence_score >= 65:
            decision = "WAIT BEFORE SELLING"
            reason = f"The AI forecast expects the {code} price to increase moderately over the next few days. Since market volatility is currently {vol_level} and confidence is relatively strong, waiting may help you secure a better exchange rate later."
            simple_summary = "Prices are rising. Wait to maximize profit."
        elif expected_change_pct <= -1.0:
            decision = "SELL NOW"
            reason = f"The forecast suggests a future decline in {code}. Selling now may protect you from taking a loss."
            simple_summary = "Prices may drop soon. Sell now."
        else:
            decision = "HOLD"
            reason = f"The market is relatively flat or unpredictable. You can hold your position or sell if you need immediate liquidity."
            simple_summary = "Market is stable. Hold or sell based on need."

    # ── Gain / Loss Scenario Calculations ─────────────────────────────
    # For BUY intent: "gain" means the buyer saves money if the price drops.
    # For SELL intent: "gain" means the seller earns more if the price rises.
    if action == "buy":
        # Gain if waiting: If price drops (negative change), waiting is a positive gain.
        wait_gain = round(-expected_change_pct, 2)
        # Worst case for buyer: highest upper-bound across the horizon
        worst_case = max([p["upper"] for p in predictions])
        worst_change = (worst_case - current_price) / current_price if current_price > 0 else 0
        worst_loss = round(- (worst_change * 100), 2)
        
        if_wait = "If you wait, you may have to buy at the new forecasted price."
        if_trade = "Buying now locks in today's exact rate."
    else:
        # Gain if waiting: If price rises (positive change), waiting is a positive gain.
        wait_gain = round(expected_change_pct, 2)
        # Worst case for seller: lowest lower-bound across the horizon
        worst_case = min([p["lower"] for p in predictions])
        worst_change = (worst_case - current_price) / current_price if current_price > 0 else 0
        worst_loss = round(worst_change * 100, 2)
        
        if_wait = "If you wait, you may be able to sell at the new forecasted price."
        if_trade = "Selling now locks in today's exact rate."

    # ── MARKET MOOD ───────────────────────────────────────────────────
    # Classifies the overall market sentiment based on expected change
    # and volatility level.
    if expected_change_pct >= 1.0:
        market_mood = "Bullish 📈"
    elif expected_change_pct <= -1.0:
        market_mood = "Bearish 📉"
    elif vol_level == "high":
        market_mood = "Unstable ⚠️"
    else:
        market_mood = "Stable ➖"

    # ── RISK LEVEL ────────────────────────────────────────────────────
    # Combines volatility and expected decline into a simple risk tier.
    if vol_level == "high":
        risk_level = "HIGH RISK"
    elif vol_level == "medium" or expected_change_pct < -2.0:
        risk_level = "MEDIUM RISK"
    else:
        risk_level = "LOW RISK"

    # ── RECOMMENDATION STRENGTH ──────────────────────────────────────
    # Signals how strongly the model backs its own recommendation,
    # based on confidence, volatility, and trend magnitude.
    if confidence_score >= 80 and vol_level != "high" and abs(expected_change_pct) >= 1.5:
        recommendation_strength = "STRONG SIGNAL"
    elif confidence_score >= 60 and vol_level != "high":
        recommendation_strength = "MODERATE SIGNAL"
    else:
        recommendation_strength = "WEAK SIGNAL"

    # ── BEST CASE / WORST CASE TEXT ──────────────────────────────────
    # Human-readable descriptions of the upside and downside scenarios.
    if action == "buy":
        best_case_text = f"You may save up to {abs(wait_gain)}% if the market drops." if wait_gain > 0 else f"You may face up to {abs(wait_gain)}% extra cost if the market rises."
        worst_case_text = f"Unexpected market volatility could increase costs by up to {abs(worst_loss)}%."
    else:
        best_case_text = f"You may gain up to {abs(wait_gain)}% extra profit if the market rises." if wait_gain > 0 else f"You could lose up to {abs(wait_gain)}% if the market drops."
        worst_case_text = f"Unexpected market volatility could reduce value by up to {abs(worst_loss)}%."

    # ── Build and return the full recommendation payload ──────────────
    return {
        "decision": decision,
        "decision_text": reason,
        "simple_summary": simple_summary,
        "reason": reason,
        "best_day_to_act": final_day["date"],
        "confidence_score": confidence_score,
        "volatility_level": vol_level,
        "market_mood": market_mood,
        "risk_level": risk_level,
        "recommendation_strength": recommendation_strength,
        "metrics": {
            "expected_gain": wait_gain,
            "worst_case_gain": worst_loss
        },
        "scenarios": {
            "if_you_wait": if_wait,
            "if_you_trade": if_trade,
            "best_case_text": best_case_text,
            "worst_case_text": worst_case_text,
            "wait": {
                "expected_gain": wait_gain,
                "worst_case_loss": worst_loss
            },
            "trade_now": {
                "gain": 0,
                "risk": 0
            }
        }
    }
