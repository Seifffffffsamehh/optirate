"""
Base provider — abstract contract that all data-source providers must follow.

This module defines the **Provider pattern** used throughout OptiRate's scraping
layer.  Every external data source (bank websites, gold price feeds, news APIs,
etc.) is implemented as a concrete subclass of ``BaseProvider``.

Architecture:
    ┌──────────────┐       ┌────────────────┐
    │ BaseProvider  │◄──────│ EgRatesProvider│  (concrete)
    │  .fetch()     │       └────────────────┘
    │  ._fetch_live │◄──────┌────────────────┐
    │  ._get_fallback       │ DahabProvider  │  (concrete)
    └──────────────┘       └────────────────┘

Key design decisions:
    - **Automatic fallback**: If ``_fetch_live()`` raises an exception or
      returns empty data, the framework transparently calls ``_get_fallback()``
      and wraps the result with diagnostic metadata (reason, latency, etc.).
    - **Latency tracking**: Every fetch is timed so downstream consumers
      (monitoring, logging) can observe provider health.
    - **Uniform result type**: All providers return ``ProviderResult``, making
      the engine layer provider-agnostic.

How to create a new provider:
    1. Subclass ``BaseProvider``.
    2. Implement the ``name`` property (unique string identifier).
    3. Implement ``_fetch_live(**kwargs)`` with your scraping / API logic.
    4. Implement ``_get_fallback(**kwargs)`` returning static or cached data.
    5. Optionally use ``self._http_get(url)`` for HTTP requests with shared
       headers and default timeout.
"""

import time
import logging
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)

# Shared HTTP headers for all providers.
# The User-Agent mimics a real browser to avoid being blocked by bank websites,
# and Accept-Language prefers Arabic (primary audience) with English fallback.
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "ar,en;q=0.9",
}

DEFAULT_TIMEOUT = 10  # seconds — aggressive timeout to prevent slow providers from blocking responses


class ProviderResult:
    """
    Encapsulates the outcome of a provider fetch with diagnostic metadata.

    Attributes:
        data:       The fetched payload — typically a list of rate dicts.
        success:    True if the live fetch returned usable data.
        fallback:   True if the data came from the static fallback path.
        reason:     Human-readable failure reason (empty on success).
                    Common values: "provider_empty", "network_error",
                    "provider_failure".
        latency_ms: Wall-clock time for the fetch attempt in milliseconds.
        source:     The provider's unique name (mirrors ``BaseProvider.name``).
    """

    __slots__ = ("data", "success", "fallback", "reason", "latency_ms", "source")

    def __init__(
        self,
        data: list | dict | None = None,
        success: bool = True,
        fallback: bool = False,
        reason: str = "",
        latency_ms: float = 0.0,
        source: str = "",
    ):
        self.data = data if data is not None else []
        self.success = success
        self.fallback = fallback
        self.reason = reason
        self.latency_ms = latency_ms
        self.source = source


class BaseProvider(ABC):
    """
    Abstract base for all data-source providers.

    Subclasses MUST implement:
        - name (property): unique identifier e.g. 'egrates'
        - _fetch_live(**kwargs): raw scraping logic, returns list[dict] or dict
        - _get_fallback(**kwargs): static fallback data
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this provider (e.g., 'egrates')."""
        ...

    @abstractmethod
    def _fetch_live(self, **kwargs) -> list | dict:
        """Perform the actual scrape / API call. Return raw parsed data."""
        ...

    @abstractmethod
    def _get_fallback(self, **kwargs) -> list | dict:
        """Return static fallback data when live fetch fails."""
        ...

    def fetch(self, **kwargs) -> ProviderResult:
        """
        Orchestrated fetch with timing, error handling, and auto-fallback.

        Execution flow:
            1. Call ``_fetch_live()`` and time the operation.
            2. If data is returned → wrap in a success ``ProviderResult``.
            3. If data is empty → log a warning and fall back.
            4. If a ``requests.RequestException`` is raised → fall back
               with reason "network_error".
            5. If any other exception is raised → fall back with reason
               "provider_failure".

        Returns:
            ProviderResult with data, success/fallback flags, and latency.
        """
        start = time.perf_counter()
        try:
            data = self._fetch_live(**kwargs)
            elapsed = (time.perf_counter() - start) * 1000

            if data:
                logger.info(
                    "[%s] Live fetch OK — %d item(s) in %.0fms",
                    self.name, len(data) if isinstance(data, list) else 1, elapsed,
                )
                return ProviderResult(
                    data=data,
                    success=True,
                    fallback=False,
                    latency_ms=round(elapsed, 1),
                    source=self.name,
                )

            # Live returned empty → fallback
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("[%s] Live fetch returned empty — using fallback", self.name)
            return self._make_fallback_result("provider_empty", elapsed, **kwargs)

        except requests.RequestException as exc:
            # Network-level failures: DNS errors, timeouts, connection resets
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("[%s] Network error: %s (%.0fms)", self.name, exc, elapsed)
            return self._make_fallback_result("network_error", elapsed, **kwargs)

        except Exception as exc:
            # Catch-all for parsing errors, unexpected HTML changes, etc.
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("[%s] Unexpected error: %s (%.0fms)", self.name, exc, elapsed)
            return self._make_fallback_result("provider_failure", elapsed, **kwargs)

    def _make_fallback_result(self, reason: str, elapsed: float, **kwargs) -> ProviderResult:
        """
        Build a ``ProviderResult`` populated with static fallback data.

        Called internally when the live fetch path fails.  The ``reason``
        parameter is propagated so consumers can distinguish between
        network errors and empty responses.
        """
        fallback_data = self._get_fallback(**kwargs)
        return ProviderResult(
            data=fallback_data,
            success=False,
            fallback=True,
            reason=reason,
            latency_ms=round(elapsed, 1),
            source=self.name,
        )

    def _http_get(self, url: str, timeout: int | None = None) -> requests.Response:
        """
        Convenience wrapper for HTTP GET with shared browser-like headers.

        All providers should use this method instead of calling
        ``requests.get()`` directly so that headers and timeout are
        applied consistently.

        Args:
            url:     Target URL to fetch.
            timeout: Per-request timeout override in seconds.
                     Defaults to ``DEFAULT_TIMEOUT`` (10s).

        Returns:
            The raw ``requests.Response`` object.
        """
        return requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout or DEFAULT_TIMEOUT,
        )
