"""
DahabMasr provider — fetches Egyptian silver prices from the JSON API.

Data source:
    dahabmasr.com exposes a two-step JSON API (auth → fetch) that returns
    current buy/sell prices for silver per gram in EGP.

Auth flow:
    1. GET ``/api/price/auth`` → returns a one-time ``nonce`` token.
    2. POST ``/api/price/fetch`` with header ``X-Price-Nonce: <nonce>``
       → returns an array of price objects.

Parsing:
    The first element of the returned array is used.  Fields ``Buy_silver``
    and ``Sell_silver`` are extracted and sanitised via ``_parse_price()``.

Validation:
    Prices must fall in the range (1, 10000) EGP per gram; values outside
    this band are treated as erroneous and discarded.

Fallback:
    A static FALLBACK_SILVER dict is returned when the API is unreachable.
"""

import re
import requests
from datetime import datetime, timezone

from services.core.base_provider import BaseProvider

# ── Configuration ────────────────────────────────────────────────────────────

# Step-1 endpoint: returns a JSON object with a short-lived ``nonce`` token.
AUTH_URL = "https://dahabmasr.com/api/price/auth"
# Step-2 endpoint: requires the nonce in the ``X-Price-Nonce`` header.
FETCH_URL = "https://dahabmasr.com/api/price/fetch"

# Static fallback used when the live API and cache are both unavailable.
# Values are approximate and should be refreshed periodically.
FALLBACK_SILVER = {
    "metal": "silver",
    "buy": 130.0,
    "sell": 125.0,
    "currency": "EGP",
}


def _parse_price(text: str | float | int) -> float | None:
    """Convert a price value (string, int, or float) to a float.

    Handles comma-separated numbers and strings with embedded currency
    symbols.  Returns None if the input is unparseable or None.

    Args:
        text: Raw price value from the API response.

    Returns:
        Cleaned float value, or None on failure.
    """
    if text is None:
        return None
    try:
        if isinstance(text, (int, float)):
            return float(text)
        cleaned = re.sub(r"[^\d.]", "", str(text).replace(",", "").strip())
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


# ── Provider ─────────────────────────────────────────────────────────────────

class DahabmasrProvider(BaseProvider):
    """Fetches silver prices from dahabmasr.com via a nonce-authenticated JSON API.

    This provider is the primary source for silver price data in the system.
    The silver engine wraps it with caching and failover logic.
    """

    @property
    def name(self) -> str:
        return "dahabmasr"

    def _fetch_live(self, **kwargs) -> dict:
        """Execute the two-step auth/fetch flow and return silver prices.

        Returns:
            Dict with keys: metal, buy, sell, currency, source, timestamp.
            Returns an empty dict if the nonce is unavailable, the response
            is malformed, or the prices fail validation.
        """
        now = datetime.now(timezone.utc).isoformat()

        # Use a session to persist cookies between the auth and fetch steps.
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
            "Accept-Language": "ar,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",  # Required by the API to accept the request.
        }
        session.headers.update(headers)

        # 1. Fetch nonce
        auth_resp = session.get(AUTH_URL, timeout=10)
        auth_resp.raise_for_status()
        auth_data = auth_resp.json()
        nonce = auth_data.get("nonce")

        if not nonce:
            return {}

        # 2. Fetch prices with nonce
        session.headers.update({"X-Price-Nonce": str(nonce)})
        fetch_resp = session.post(FETCH_URL, timeout=10)
        fetch_resp.raise_for_status()
        data = fetch_resp.json()

        if not data or not isinstance(data, list):
            return {}  # Unexpected response shape — treat as failure.

        # The API returns an array; the first element holds current prices.
        item = data[0]

        # 3. Extract and parse prices
        buy_price = _parse_price(item.get("Buy_silver"))
        sell_price = _parse_price(item.get("Sell_silver"))

        if buy_price is None or sell_price is None:
            return {}

        # 4. Validation (silver gram price must be > 1 and < 10000)
        if not (1 < buy_price < 10000) or not (1 < sell_price < 10000):
            return {}

        return {
            "metal": "silver",
            "buy": buy_price,
            "sell": sell_price,
            "currency": "EGP",
            "source": self.name,
            "timestamp": now,
        }

    def _get_fallback(self, **kwargs) -> dict:
        """Return hardcoded silver prices as a last-resort fallback."""
        now = datetime.now(timezone.utc).isoformat()
        return {**FALLBACK_SILVER, "source": self.name, "timestamp": now}
