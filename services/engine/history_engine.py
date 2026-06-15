"""
History engine — orchestrates the CBE provider with DB storage and caching.

Purpose:
    This module coordinates background historical ingestion (via `sync_daily_history`)
    and exposes historical query methods (`get_history`) for forecasting.
    
Caching:
    - History queries are cached using the global `cache_manager` with the domain prefix `history_`.
    - Every successful daily sync invalidates the cached history values to guarantee data freshness.
"""

import logging

from extensions import db
from models.exchange_history import ExchangeHistory
from services.cache.cache_manager import cache_manager
from services.core.base_provider import ProviderResult
from services.providers.cbe_provider import CbeProvider

logger = logging.getLogger(__name__)

# ── Singleton provider ──────────────────────────────────────────────────────


_provider = CbeProvider()

# ── Health metrics ───────────────────────────────────────────────────────────

_metrics: list[dict] = []


def _record_metric(result: ProviderResult):
    _metrics.append({
        "provider": result.source,
        "status": "success" if result.success else "fail",
        "latency_ms": result.latency_ms,
        "fallback_used": result.fallback,
        "reason": result.reason,
    })
    if len(_metrics) > 100:
        del _metrics[:50]


def get_metrics() -> list[dict]:
    return list(_metrics)


# ── Import / Store ───────────────────────────────────────────────────────────

def sync_daily_history(app) -> dict:
    """
    Fetch live exchange rate data and append/update it in the history database.
    This runs daily to ensure the model uses the most recent 'Ground Truth'.
    """
    from datetime import datetime
    from sqlalchemy.dialects.mysql import insert

    try:
        rates = _provider._fetch_live()
    except Exception as e:
        logger.error(f"Failed to fetch live rates for history sync: {e}")
        return {"status": "error", "message": "Failed to fetch live rates."}

    if not rates:
        logger.error("No live rates returned from CBE provider.")
        return {
            "status": "error",
            "message": "No live rates returned from CBE provider.",
        }

    inserted = 0
    today = datetime.now().date()
    
    # Validation: Check if USD is missing
    if not any(r.get("currency") == "USD" for r in rates):
        logger.error("ALERT: USD rate is missing from today's scraped rates!")

    with app.app_context():
        for record in rates:
            currency_code = record.get("currency")
            rate = record.get("rate")
            source = record.get("source", "CBE")

            if not currency_code or not rate:
                continue
                
            # Validation: Check if rate hasn't changed for multiple days
            last_records = (
                ExchangeHistory.query
                .filter_by(currency=currency_code)
                .order_by(ExchangeHistory.date.desc())
                .limit(3)
                .all()
            )
            
            if len(last_records) == 3 and all(r.rate == rate for r in last_records):
                logger.warning(f"WARNING: Rate for {currency_code} hasn't changed from {rate} for the last 3 days.")

            stmt = insert(ExchangeHistory).values(
                currency=currency_code,
                date=today,
                rate=rate,
                source=source
            )
            # Do NOT overwrite old data, just ignore if duplicate
            stmt = stmt.prefix_with('IGNORE')
            
            try:
                result = db.session.execute(stmt)
                if result.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.error(f"Error inserting rate for {currency_code}: {e}")

        db.session.commit()
        
        # Invalidate cache for history
        from services.cache.cache_manager import cache_manager
        cache_manager.clear_prefix("history_")

    logger.info(f"Daily history sync completed. Inserted {inserted} new records.")
    return {"inserted": inserted}


# ── Public API ───────────────────────────────────────────────────────────────

def get_history(currency_code: str, limit: int = 90) -> list[dict]:
    """
    Get stored historical rates for a currency.

    Args:
        currency_code: ISO code (e.g., 'USD').
        limit: Max records to return (default 90).

    Returns:
        List of {id, currency, date, rate} dicts ordered by date descending.
    """
    code = currency_code.upper()
    cache_key = f"history_{code}_{limit}"

    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached

    records = (
        ExchangeHistory.query
        .filter_by(currency=code)
        .order_by(ExchangeHistory.date.desc())
        .limit(limit)
        .all()
    )

    result = [r.to_dict() for r in records]
    cache_manager.set(cache_key, result, domain="history")
    return result
