"""
eDahab provider — scrapes edahabapp.com for Egyptian gold prices.

Difference from DahabMasr:
    - DahabMasr uses a **JSON API** with nonce authentication and returns
      only **silver** prices.
    - eDahab scrapes **HTML** from edahabapp.com and extracts **gold**
      prices across multiple karats (14K, 18K, 21K, 24K), plus gold coins
      and the international ounce price in USD.

Parsing strategy:
    1. The page is fetched via HTTP GET (through BaseProvider._http_get).
    2. BeautifulSoup finds all text nodes matching a karat label (Arabic or
       numeric, e.g. "عيار 24" or "24").
    3. For each match, the parent container's text is scanned with a regex
       to extract all numeric values > 100 (to filter out noise).
    4. The first two qualifying numbers are taken as buy (max) and sell (min).
    5. De-duplication ensures each karat label appears only once in results.

Fallback:
    A static FALLBACK_GOLD list provides approximate EGP prices for 24K,
    21K, and 18K when the live scrape fails.
"""

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from services.core.base_provider import BaseProvider

# ── Configuration ────────────────────────────────────────────────────────────

# Home page of edahabapp.com — gold prices are rendered inline in the HTML.
GOLD_URL = "https://edahabapp.com/"

# Maps page text labels (Arabic or short numeric) to standardised karat names.
# Multiple Arabic spellings are included because the site uses inconsistent
# orthography (e.g. with/without the definite article or different hamza forms).
KARAT_MAP = {
    "24": "24K",
    "21": "21K",
    "18": "18K",
    "14": "14K",
    "عيار 24": "24K",
    "عيار 21": "21K",
    "عيار 18": "18K",
    "عيار 14": "14K",
    "الجنيه الذهب": "Coin",       # Egyptian gold pound (≈ 8g of 21K gold)
    "جنيه ذهب": "Coin",
    "الأونصة بالدولار": "Ounce USD",  # International gold ounce in USD
    "أونصة بالدولار": "Ounce USD",
    "الاونصة بالدولار": "Ounce USD",
    "سعر الأوقية عالمياً": "Ounce USD",
    "الأوقية": "Ounce USD"
}

# Approximate EGP-per-gram fallback prices for the three most-traded karats.
FALLBACK_GOLD = [
    {"karat": "24K", "buy": 5350, "sell": 5300, "currency": "EGP"},
    {"karat": "21K", "buy": 4680, "sell": 4630, "currency": "EGP"},
    {"karat": "18K", "buy": 4015, "sell": 3965, "currency": "EGP"},
]


def _parse_price(text: str) -> float | None:
    """Strip non-numeric characters and convert to float.

    Args:
        text: Raw text snippet that may contain commas, currency symbols, etc.

    Returns:
        Parsed float, or None on failure.
    """
    try:
        cleaned = re.sub(r"[^\d.]", "", text.strip())
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


# ── Provider ─────────────────────────────────────────────────────────────────

class EdahabProvider(BaseProvider):
    """Scrapes edahabapp.com for gold karat prices (buy and sell per gram).

    Unlike the DahabMasr provider (which uses a JSON API for silver),
    this provider parses raw HTML and uses regex-based price extraction
    from DOM containers surrounding each karat label.
    """

    @property
    def name(self) -> str:
        return "edahabapp"

    def _fetch_live(self, **kwargs) -> list[dict]:
        """Scrape gold prices from the edahabapp.com home page.

        Returns:
            List of dicts with keys: karat, buy, sell, currency, source, timestamp.
            Returns an empty list if the page cannot be fetched or parsed.
        """
        resp = self._http_get(GOLD_URL)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        now = datetime.now(timezone.utc).isoformat()
        results = []

        # For each known karat label, find matching text nodes in the DOM,
        # then walk up to the grandparent container to extract numeric prices.
        for karat_key, karat_label in KARAT_MAP.items():
            elements = soup.find_all(string=re.compile(re.escape(karat_key)))
            for elem in elements:
                parent = elem.find_parent()
                if not parent:
                    continue
                container = parent.find_parent()
                if not container:
                    continue

                # Extract all number-like substrings from the container text.
                prices = re.findall(r"[\d,]+\.?\d*", container.get_text())
                # Filter out small numbers (page noise like dates, IDs, etc.).
                price_vals = []
                for p in prices:
                    val = _parse_price(p.replace(",", ""))
                    if val and val > 100:  # Gold gram prices are always > 100 EGP.
                        price_vals.append(val)

                # Only add if we found at least one valid price and this
                # karat hasn't already been recorded (de-duplication guard).
                if len(price_vals) >= 1 and not any(
                    r["karat"] == karat_label for r in results
                ):
                    results.append({
                        "karat": karat_label,
                        # When two prices exist, the higher is buy, the lower is sell.
                        "buy": max(price_vals[:2]) if len(price_vals) >= 2 else price_vals[0],
                        "sell": min(price_vals[:2]) if len(price_vals) >= 2 else price_vals[0],
                        # Ounce prices are denominated in USD; all others in EGP.
                        "currency": "USD" if "USD" in karat_label else "EGP",
                        "source": self.name,
                        "timestamp": now,
                    })

        return results

    def _get_fallback(self, **kwargs) -> list[dict]:
        """Return hardcoded gold prices for 24K, 21K, and 18K."""
        now = datetime.now(timezone.utc).isoformat()
        return [
            {**g, "source": self.name, "timestamp": now}
            for g in FALLBACK_GOLD
        ]
