"""Silver engine — orchestrates the DahabMasr provider with caching and failover."""

import logging

from services.cache.cache_manager import cache_manager
from services.core.data_normalizer import normalize_silver
from services.core.base_provider import ProviderResult
from services.providers.dahabmasr_provider import DahabmasrProvider

logger = logging.getLogger(__name__)

# ── Singleton provider ──────────────────────────────────────────────────────

_provider = DahabmasrProvider()

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
    """Return recent provider health metrics."""
    return list(_metrics)


# ── Failover pipeline ───────────────────────────────────────────────────────

def _fetch_with_failover() -> tuple[dict, bool, str]:
    """
    3-tier failover:
      1. Live provider
      2. Last-known-good cache
      3. Static fallback
    """
    cache_key = "silver"

    result = _provider.fetch()
    _record_metric(result)

    if result.success and result.data:
        cache_manager.set(cache_key, result.data, domain="silver")
        return result.data, False, ""

    lkg = cache_manager.get_lkg(cache_key)
    if lkg:
        age = cache_manager.get_lkg_age(cache_key)
        logger.warning("[silver] Using LKG cache (age=%.0fs)", age or 0)
        return lkg, True, "cache_expired"

    if result.data:
        return result.data, True, result.reason

    return {}, True, "no_data_available"


# ── Public API ───────────────────────────────────────────────────────────────

def get_silver_prices() -> dict:
    """
    Fetch silver prices.

    Returns:
        **Normalized** silver price dict.
    """
    cache_key = "silver"

    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached

    data, is_fallback, reason = _fetch_with_failover()

    if not data:
        return normalize_silver(
            {"buy": 0, "sell": 0},
            fallback=True,
            reason="no_data_available",
            source="dahabmasr",
        )

    normalized = normalize_silver(
        data,
        fallback=is_fallback,
        reason=reason,
        source=data.get("source", "dahabmasr"),
    )
    cache_manager.set(cache_key, normalized, domain="silver")
    return normalized
