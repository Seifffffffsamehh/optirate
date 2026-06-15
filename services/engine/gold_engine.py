"""Gold engine — orchestrates the eDahab provider with caching and failover."""

import logging

from services.cache.cache_manager import cache_manager
from services.core.data_normalizer import normalize_gold
from services.core.base_provider import ProviderResult
from services.providers.edahab_provider import EdahabProvider

logger = logging.getLogger(__name__)

# ── Singleton provider ──────────────────────────────────────────────────────

_provider = EdahabProvider()

# ── Health metrics ───────────────────────────────────────────────────────────

_metrics: list[dict] = []


def _record_metric(result: ProviderResult):
    """Append a health metric for this fetch."""
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
    """Return recent provider health metrics."""
    return list(_metrics)


# ── Failover pipeline ───────────────────────────────────────────────────────

def _fetch_with_failover() -> tuple[list[dict], bool, str]:
    """
    3-tier failover:
      1. Live provider
      2. Last-known-good cache
      3. Static fallback
    """
    cache_key = "gold_all"

    result = _provider.fetch()
    _record_metric(result)

    if result.success and result.data:
        cache_manager.set(cache_key, result.data, domain="gold")
        return result.data, False, ""

    lkg = cache_manager.get_lkg(cache_key)
    if lkg:
        age = cache_manager.get_lkg_age(cache_key)
        logger.warning("[gold] Using LKG cache (age=%.0fs)", age or 0)
        return lkg, True, "cache_expired"

    if result.data:
        return result.data, True, result.reason

    return [], True, "no_data_available"


# ── Public API ───────────────────────────────────────────────────────────────

def get_gold_prices(role: str = "free") -> list[dict]:
    """
    Fetch gold prices.

    Args:
        role: Kept for backward compatibility, but UI now handles gating.

    Returns:
        List of **normalized** gold price dicts.
    """
    cache_key = "gold_all"

    # Check fresh cache
    cached = cache_manager.get(cache_key)
    if cached is not None:
        all_prices = cached
    else:
        data, is_fallback, reason = _fetch_with_failover()
        all_prices = [
            normalize_gold(
                r,
                fallback=is_fallback,
                reason=reason,
                source=r.get("source", "edahabapp"),
            )
            for r in data
        ]
        if all_prices:
            cache_manager.set(cache_key, all_prices, domain="gold")

    return all_prices
