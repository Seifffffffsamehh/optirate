"""Currency engine — orchestrates the Egrates provider with caching and failover."""

import logging
from datetime import datetime, timezone

from services.cache.cache_manager import cache_manager
from services.core.data_normalizer import normalize_currency
from services.core.base_provider import ProviderResult
from services.providers.egrates_provider import EgratesProvider

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

REQUIRED_CURRENCIES = [
    "USD", "EUR", "SAR", "AED", "KWD", "QAR", "GBP", "AUD", "CAD", "JPY", "CNY", "OMR"
]

FREE_CURRENCIES = REQUIRED_CURRENCIES

# ── Singleton provider ──────────────────────────────────────────────────────

_provider = EgratesProvider()

# ── Health metrics ───────────────────────────────────────────────────────────

_metrics: list[dict] = []


def _record_metric(result: ProviderResult, currency: str):
    """Append a health metric for this fetch."""
    _metrics.append({
        "provider": result.source,
        "currency": currency,
        "status": "success" if result.success else "fail",
        "latency_ms": result.latency_ms,
        "fallback_used": result.fallback,
        "reason": result.reason,
    })
    # Keep only last 100 entries
    if len(_metrics) > 100:
        del _metrics[:50]


def get_metrics() -> list[dict]:
    """Return recent provider health metrics."""
    return list(_metrics)


# ── Failover pipeline ───────────────────────────────────────────────────────

def _fetch_with_failover(code: str) -> tuple[list[dict], bool, str]:
    """
    3-tier failover:
      1. Live provider
      2. Stale cache (last-known-good)
      3. Static fallback (inside provider)

    Returns:
        (data, is_fallback, reason)
    """
    cache_key = f"currency_{code}"

    # Tier 1: Live fetch
    result = _provider.fetch(currency=code)
    _record_metric(result, code)

    if result.success and result.data:
        cache_manager.set(cache_key, result.data, domain="currency")
        return result.data, False, ""

    # Tier 2: Last-known-good cache
    lkg = cache_manager.get_lkg(cache_key)
    if lkg:
        age = cache_manager.get_lkg_age(cache_key)
        logger.warning(
            "[currency] Using LKG cache for %s (age=%.0fs)", code, age or 0,
        )
        return lkg, True, "cache_expired"

    # Tier 3: Static fallback (already provided by the provider result)
    if result.data:
        return result.data, True, result.reason

    return [], True, "no_data_available"


from concurrent.futures import ThreadPoolExecutor

# ── Public API ───────────────────────────────────────────────────────────────

def get_currency_rates(
    currency_code: str | None = None,
    role: str = "free",
    force_refresh: bool = False,
) -> list[dict]:
    """
    Fetch exchange rates for one or all required currencies.

    Args:
        currency_code: Specific currency code, or None for all.
        role: User role — 'free' sees limited currencies, 'premium'/'admin' sees all.

    Returns:
        List of **normalized** rate dicts sorted by best sell rate.
    """
    codes = REQUIRED_CURRENCIES if role in ("premium", "admin") else FREE_CURRENCIES

    if currency_code:
        code = currency_code.upper()
        if code not in REQUIRED_CURRENCIES:
            return []
        if role == "free" and code not in FREE_CURRENCIES:
            return []
        codes = [code]

    all_rates = []
    
    def fetch_and_normalize(code):
        # Check fresh cache first
        cache_key = f"currency_{code}"
        if not force_refresh:
            cached = cache_manager.get(cache_key)
            if cached is not None:
                return cached

        data, is_fallback, reason = _fetch_with_failover(code)

        # Normalize every record
        normalized = [
            normalize_currency(
                r,
                fallback=is_fallback,
                reason=reason,
                source=r.get("source", "egrates"),
            )
            for r in data
        ]

        if normalized:
            cache_manager.set(cache_key, normalized, domain="currency")
        return normalized

    # Use ThreadPoolExecutor for parallel fetching
    with ThreadPoolExecutor(max_workers=len(codes)) as executor:
        results = list(executor.map(fetch_and_normalize, codes))

    for normalized_data in results:
        all_rates.extend(normalized_data)

    # Sort by best sell rate (lowest first = best for buyer)
    all_rates.sort(key=lambda r: r.get("sell", float("inf")))

    print(f"Fetched {len(all_rates)} bank records across {len(codes)} currencies.")
    return all_rates


def _parse_iso_ts(ts: str | None) -> datetime | None:
    """Safely parse ISO timestamps that may end with Z."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_stale(ts: str | None, max_age_hours: int) -> bool:
    dt = _parse_iso_ts(ts)
    if dt is None:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() > (max_age_hours * 3600)


def are_rates_stale(rates: list[dict], max_age_hours: int = 6) -> bool:
    """
    Consider rates stale when every bank record is old, or all records are fallback.
    """
    if not rates:
        return True
    has_fresh = any(not _is_stale(r.get("timestamp"), max_age_hours) for r in rates)
    all_fallback = all(bool(r.get("fallback")) for r in rates)
    return (not has_fresh) or all_fallback


def get_average_currency_rates(
    currency_code: str | None = None,
    role: str = "free",
    max_age_hours: int = 6,
) -> list[dict]:
    """
    Compute on-the-fly bank averages per currency from latest provider rows.
    If stale, clear currency cache and force an immediate re-fetch.
    """
    # Requirement: average cache TTL must stay <= 30 minutes.
    cache_manager.set_ttl("currency_avg", 1800)

    codes = REQUIRED_CURRENCIES if role in ("premium", "admin") else FREE_CURRENCIES
    if currency_code:
        code = currency_code.upper()
        if code not in REQUIRED_CURRENCIES:
            return []
        if role == "free" and code not in FREE_CURRENCIES:
            return []
        codes = [code]

    cache_key = "currency_avg_all" if not currency_code else f"currency_avg_{codes[0]}"
    cached_avg = cache_manager.get(cache_key)
    if cached_avg is not None:
        return cached_avg

    rates = get_currency_rates(currency_code=currency_code, role=role)
    if are_rates_stale(rates, max_age_hours=max_age_hours):
        logger.warning("[currency] stale data detected. Clearing currency cache and forcing re-scrape.")
        cache_manager.clear_prefix("currency_")
        rates = get_currency_rates(currency_code=currency_code, role=role, force_refresh=True)

    grouped: dict[str, list[dict]] = {}
    for row in rates:
        code = row.get("currency")
        if not code:
            continue
        grouped.setdefault(code, []).append(row)

    averages: list[dict] = []
    for code in codes:
        banks = grouped.get(code, [])
        if not banks:
            continue

        sell_values = [float(b.get("sell", 0)) for b in banks if b.get("sell") is not None]
        buy_values = [float(b.get("buy", 0)) for b in banks if b.get("buy") is not None]
        if not sell_values or not buy_values:
            continue

        # Latest timestamp among banks used for this currency.
        parsed_times = [t for t in (_parse_iso_ts(b.get("timestamp")) for b in banks) if t]
        latest_ts = max(parsed_times).isoformat() if parsed_times else None

        averages.append({
            "currency": code,
            "avg_buy": round(sum(buy_values) / len(buy_values), 4),
            "avg_sell": round(sum(sell_values) / len(sell_values), 4),
            "bank_count": len(sell_values),
            "banks_used": [b.get("bank", "Unknown") for b in banks],
            "sources_used": sorted({b.get("source", "unknown") for b in banks}),
            "last_updated": latest_ts,
            "is_stale": are_rates_stale(banks, max_age_hours=max_age_hours),
        })

    cache_manager.set(cache_key, averages, domain="currency_avg")
    return averages


def get_live_spot_rate(currency_code: str) -> float:
    """
    Fetch the latest market SELL price average across all banks.
    This acts as the single source of truth for the current spot rate across the entire project.
    """
    code = currency_code.upper()
    averages = get_average_currency_rates(currency_code=code, role="premium")
    if averages:
        spot_rate = averages[0].get("avg_sell", 0.0)
        bank_count = averages[0].get("bank_count", 0)
        last_updated = averages[0].get("last_updated", "unknown")
        logger.info(f"[SPOT RATE] {code}: {spot_rate} EGP (Banks: {bank_count}, Updated: {last_updated})")
        return spot_rate
    
    logger.warning(f"[SPOT RATE] Failed to fetch live spot rate for {code}. Returning 0.0")
    return 0.0
