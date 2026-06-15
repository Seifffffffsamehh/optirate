"""
Advanced in-memory cache manager with TTL, versioning, and last-known-good snapshots.

This module provides the caching layer for all OptiRate data domains (currency
rates, gold prices, silver prices, historical records, and AI forecasts).

Architecture & Design Decisions:
    - **In-memory dict storage**: Chosen over Redis/Memcached for deployment
      simplicity.  Suitable for a single-process Flask application.
    - **Per-domain TTLs**: Different data types have different freshness
      requirements.  Currency/gold/silver rates expire after 5 minutes;
      historical data after 10 minutes.  Custom TTLs can be set at runtime.
    - **Cache key convention**: Keys are prefixed with their domain name
      (e.g. ``"currency_USD_premium"``).  The TTL lookup matches on this
      prefix, so new domains get the correct TTL automatically.
    - **Last-Known-Good (LKG) failover**: Every successful ``set()`` also
      persists data into a separate LKG store that **never expires**.  When
      both the live provider and the fresh cache fail, the engine layer can
      call ``get_lkg()`` to serve stale-but-valid data rather than returning
      an error to the user.
    - **Versioning**: Each cache key tracks an auto-incrementing version
      number.  This allows downstream consumers to detect whether the cache
      has been refreshed since their last read (useful for ETags / polling).
    - **Thread safety**: All reads and writes are guarded by a single
      ``threading.Lock``.  This is sufficient for Flask's threaded request
      model and prevents race conditions between concurrent requests.

Usage::

    from services.cache.cache_manager import cache_manager

    # Store data
    cache_manager.set("currency_USD_premium", rate_list, domain="currency")

    # Retrieve (returns None if TTL expired)
    data = cache_manager.get("currency_USD_premium")

    # Failover to last-known-good
    data = data or cache_manager.get_lkg("currency_USD_premium")
"""

import time
import logging
from threading import Lock

logger = logging.getLogger(__name__)

# ── Default TTLs per data domain ─────────────────────────────────────────────
# Values are in seconds.  These can be overridden at runtime via set_ttl().

DEFAULT_TTLS = {
    "currency": 300,   # 5 min  — bank rates update frequently
    "gold": 300,       # 5 min  — precious metal prices are volatile
    "silver": 300,     # 5 min
    "history": 600,    # 10 min — historical records change less often
}


class CacheEntry:
    """
    Single cache entry with metadata.

    Attributes:
        data:      The cached payload (list, dict, or any serializable type).
        timestamp: Unix epoch time when the entry was written (for TTL checks).
        version:   Auto-incrementing integer — incremented each time the same
                   key is overwritten.
        domain:    Logical data domain (e.g. "currency") for grouping/TTL.
    """

    __slots__ = ("data", "timestamp", "version", "domain")

    def __init__(self, data, domain: str = "", version: int = 1):
        self.data = data
        self.timestamp = time.time()
        self.version = version
        self.domain = domain


class CacheManager:
    """
    Thread-safe in-memory cache with per-domain TTLs, auto-incrementing
    version numbers, and a last-known-good (LKG) snapshot store for failover.

    Two parallel stores are maintained:
        ``_store`` — active cache (subject to TTL expiry).
        ``_lkg``   — last-known-good snapshots (never expire, only overwritten
                     by newer successful data).

    All public methods acquire ``_lock`` before accessing either store,
    ensuring safe concurrent access from multiple Flask request threads.
    """

    def __init__(self):
        self._store: dict[str, CacheEntry] = {}
        self._lkg: dict[str, CacheEntry] = {}  # last-known-good (never expires)
        self._lock = Lock()
        self._ttls = dict(DEFAULT_TTLS)

    # ── Configuration ────────────────────────────────────────────────────

    def set_ttl(self, domain: str, seconds: int):
        """
        Override the TTL for a specific domain at runtime.

        This is useful for data types not covered by DEFAULT_TTLS (e.g.
        AI forecast predictions cached for 1 hour).
        """
        self._ttls[domain] = seconds

    def _get_ttl(self, key: str) -> int:
        """
        Determine TTL for a key based on its domain prefix.

        Iterates through registered domains and returns the TTL of the
        first domain whose name is a prefix of the cache key.  Falls
        back to 300 seconds (5 min) if no domain matches.
        """
        for domain, ttl in self._ttls.items():
            if key.startswith(domain):
                return ttl
        return 300  # default 5 min

    # ── Core operations ──────────────────────────────────────────────────

    def get(self, key: str):
        """
        Return cached data if still within TTL, else None.

        This is a read-only operation — it does NOT touch the LKG store
        and does not remove expired entries (lazy expiry).
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ttl = self._get_ttl(key)
            # Check freshness: entry age must be less than the domain TTL
            if (time.time() - entry.timestamp) < ttl:
                return entry.data
            return None

    def set(self, key: str, data, domain: str = ""):
        """
        Store fresh data and also update the last-known-good snapshot.

        The version number is auto-incremented from the previous entry's
        version (or starts at 1 for new keys).  The LKG store is only
        updated when ``data`` is truthy, preventing empty/failed fetches
        from overwriting valid fallback data.
        """
        with self._lock:
            # Retrieve the previous version for auto-increment
            prev_version = 0
            if key in self._store:
                prev_version = self._store[key].version

            entry = CacheEntry(data, domain=domain, version=prev_version + 1)
            self._store[key] = entry

            # Only persist to LKG if data is non-empty — this ensures the
            # LKG store always contains the last *valid* data snapshot.
            if data:
                self._lkg[key] = CacheEntry(
                    data, domain=domain, version=entry.version,
                )

    def get_lkg(self, key: str):
        """
        Return the last-known-good data regardless of TTL.

        Used during failover when both the live provider and the fresh
        cache miss.  LKG data may be stale, but it is guaranteed to be
        the most recent *non-empty* value that was successfully cached.
        """
        with self._lock:
            entry = self._lkg.get(key)
            return entry.data if entry else None

    def get_lkg_age(self, key: str) -> float | None:
        """
        Return the age (in seconds) of the LKG entry, or None if no
        LKG data exists for the key.  Useful for monitoring/logging how
        stale the fallback data is.
        """
        with self._lock:
            entry = self._lkg.get(key)
            return round(time.time() - entry.timestamp, 1) if entry else None

    def get_version(self, key: str) -> int:
        """
        Return the current version number for a cache key.

        Returns 0 if the key has never been set.  Useful for ETag-like
        change detection.
        """
        with self._lock:
            entry = self._store.get(key)
            return entry.version if entry else 0

    def clear(self, key: str | None = None):
        """
        Clear a specific key or the entire active cache.

        The LKG store is intentionally **preserved** so that failover
        data remains available even after a manual cache clear.
        """
        with self._lock:
            if key:
                self._store.pop(key, None)
            else:
                self._store.clear()

    def clear_prefix(self, prefix: str):
        """
        Clear all active cache keys that start with a given prefix.

        Useful for bulk-invalidating an entire data domain, e.g.
        ``cache_manager.clear_prefix("currency")`` removes all cached
        currency entries without affecting gold or silver caches.
        """
        with self._lock:
            keys_to_delete = [k for k in self._store.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                self._store.pop(key, None)

    def stats(self) -> dict:
        """
        Return cache statistics for monitoring and debugging.

        Returns a dict with:
            - active_entries: Number of entries in the active cache.
            - lkg_entries:    Number of entries in the LKG store.
            - keys:           List of all active cache keys.
        """
        with self._lock:
            return {
                "active_entries": len(self._store),
                "lkg_entries": len(self._lkg),
                "keys": list(self._store.keys()),
            }


# ── Module-level singleton ───────────────────────────────────────────────────
# A single CacheManager instance is shared across the entire application.
# Import this directly: ``from services.cache.cache_manager import cache_manager``

cache_manager = CacheManager()
