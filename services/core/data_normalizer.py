"""
Data normalizer — enforces a single, consistent output schema across all data types.

Every provider in OptiRate may return data in slightly different shapes.  This
module sits between the raw provider output and the API response layer,
transforming heterogeneous dicts into a guaranteed schema that downstream
consumers (API routes, caching, AI service) can rely on.

Supported data types:
    - **Currency** rates  (``normalize_currency``)
    - **Gold** prices     (``normalize_gold``)
    - **Silver** prices   (``normalize_silver``)
    - **History** records (``normalize_history``)
    - **News** articles   (``normalize_news``)

Design notes:
    - Missing numeric fields default to ``0`` (via ``float(raw.get(..., 0))``).
    - Missing timestamps are filled with the current UTC time in ISO-8601.
    - A ``fallback`` boolean flag is always included.  When ``True``, an
      additional ``reason`` key is injected explaining why fallback data was
      used (e.g. "network_error").  When ``False``, ``reason`` is omitted
      entirely to keep the payload clean.
"""

from datetime import datetime, timezone


def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Currency Rate Normalizer
# ---------------------------------------------------------------------------

def normalize_currency(
    raw: dict,
    *,
    fallback: bool = False,
    reason: str = "",
    source: str = "",
) -> dict:
    """
    Normalize a currency rate record to the unified schema.

    Output schema::

        {
            "source":    str,   # Provider identifier (e.g. "egrates")
            "currency":  str,   # ISO currency code (e.g. "USD")
            "buy":       float, # Bank buy rate
            "sell":      float, # Bank sell rate
            "bank":      str,   # Bank name
            "timestamp": str,   # ISO-8601 UTC timestamp
            "fallback":  bool,  # Whether this is fallback data
            "reason":    str,   # (only present when fallback=True)
        }

    Required input keys: currency, buy, sell.
    Optional input keys: bank, timestamp.
    """
    return {
        "source": source or raw.get("source", "unknown"),
        "currency": raw.get("currency", ""),
        "buy": float(raw.get("buy", 0)),
        "sell": float(raw.get("sell", 0)),
        "bank": raw.get("bank", ""),
        "timestamp": raw.get("timestamp") or _now_iso(),
        "fallback": fallback,
        # Only include "reason" when serving fallback data to keep success payloads clean
        **({"reason": reason} if fallback else {}),
    }


# ---------------------------------------------------------------------------
# Gold Price Normalizer
# ---------------------------------------------------------------------------

def normalize_gold(
    raw: dict,
    *,
    fallback: bool = False,
    reason: str = "",
    source: str = "",
) -> dict:
    """
    Normalize a gold price record to the unified schema.

    Output schema::

        {
            "source":    str,   # Provider identifier (default "edahabapp")
            "currency":  str,   # Price currency (default "EGP")
            "karat":     str,   # Gold purity (e.g. "24", "21", "18")
            "buy":       float, # Buy price per gram
            "sell":      float, # Sell price per gram
            "timestamp": str,   # ISO-8601 UTC timestamp
            "fallback":  bool,
            "reason":    str,   # (only when fallback=True)
        }

    Required input keys: karat, buy, sell.
    """
    return {
        "source": source or raw.get("source", "edahabapp"),
        "currency": raw.get("currency", "EGP"),
        "karat": raw.get("karat", ""),
        "buy": float(raw.get("buy", 0)),
        "sell": float(raw.get("sell", 0)),
        "timestamp": raw.get("timestamp") or _now_iso(),
        "fallback": fallback,
        **({"reason": reason} if fallback else {}),
    }


# ---------------------------------------------------------------------------
# Silver Price Normalizer
# ---------------------------------------------------------------------------

def normalize_silver(
    raw: dict,
    *,
    fallback: bool = False,
    reason: str = "",
    source: str = "",
) -> dict:
    """
    Normalize a silver price record to the unified schema.

    If ``price_per_gram`` is not present in the raw data, it is computed
    as the midpoint (average) of the buy and sell prices.

    Output schema::

        {
            "source":         str,   # Provider identifier (default "dahabmasr")
            "currency":       str,   # Price currency (default "EGP")
            "metal":          str,   # Always "silver"
            "buy":            float, # Buy price per gram
            "sell":           float, # Sell price per gram
            "price_per_gram": float, # Midpoint or explicit value
            "timestamp":      str,
            "fallback":       bool,
            "reason":         str,   # (only when fallback=True)
        }

    Required input keys: buy, sell.
    """
    buy = float(raw.get("buy", 0))
    sell = float(raw.get("sell", 0))
    return {
        "source": source or raw.get("source", "dahabmasr"),
        "currency": raw.get("currency", "EGP"),
        "metal": "silver",
        "buy": buy,
        "sell": sell,
        # Derive per-gram price from the buy/sell midpoint when not explicitly provided
        "price_per_gram": raw.get("price_per_gram") or round((buy + sell) / 2, 2),
        "timestamp": raw.get("timestamp") or _now_iso(),
        "fallback": fallback,
        **({"reason": reason} if fallback else {}),
    }


# ---------------------------------------------------------------------------
# Historical Rate Normalizer
# ---------------------------------------------------------------------------

def normalize_history(raw: dict) -> dict:
    """
    Normalize a historical exchange rate record.

    This normalizer is simpler than the others because history records are
    sourced internally (from the DB) and don't carry fallback metadata.

    Output schema::

        {
            "id":       int | None, # Database primary key
            "currency": str,        # ISO currency code
            "date":     str,        # Date string (YYYY-MM-DD)
            "rate":     float,      # Exchange rate value
        }
    """
    return {
        "id": raw.get("id"),
        "currency": raw.get("currency", ""),
        "date": str(raw.get("date", "")),
        "rate": float(raw.get("rate", 0)),
    }


# ---------------------------------------------------------------------------
# News Article Normalizer
# ---------------------------------------------------------------------------

def normalize_news(
    raw: dict,
    *,
    fallback: bool = False,
    reason: str = "",
    source: str = "",
) -> dict:
    """
    Normalize a news article record to the unified schema.

    Output schema::

        {
            "title":        str,  # Article headline
            "source":       str,  # News source identifier
            "url":          str,  # Link to the full article
            "published_at": str,  # ISO-8601 publication timestamp
            "image":        str,  # Thumbnail / hero image URL
            "fallback":     bool,
            "reason":       str,  # (only when fallback=True)
        }
    """
    return {
        "title": raw.get("title", ""),
        "source": source or raw.get("source", "unknown"),
        "url": raw.get("url", ""),
        "published_at": raw.get("published_at") or _now_iso(),
        "image": raw.get("image", ""),
        "fallback": fallback,
        **({"reason": reason} if fallback else {}),
    }
