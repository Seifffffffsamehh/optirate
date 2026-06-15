"""
Egrates provider — scrapes egrates.com for Egyptian bank exchange rates.

Scraping strategy:
    Each currency has its own page at ``https://egrates.com/currency/<code>``.
    The page contains a single <table> where each row represents a different
    Egyptian bank's buy and sell rates for that currency.

Rate extraction:
    For every table row (bank):
    1. The bank name comes from column 0.
    2. Buy rate is read from column 1 and sell rate from column 2.
    3. Each cell may embed the value in an ``<i data-value="...">`` attribute,
       an ``<a>`` tag's text, or as raw cell text.  The code tries all three
       sources in priority order to handle layout variations.

Excluded banks:
    Some banks are excluded because they report unreliable or outdated rates.

Fallback:
    A hardcoded FALLBACK_RATES dictionary provides last-resort rates per
    currency when the live scrape fails entirely.
"""

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from services.core.base_provider import BaseProvider

# ── Configuration ────────────────────────────────────────────────────────────

# Template URL — ``{code}`` is replaced with the lowercase currency code (e.g. "usd").
BASE_URL = "https://egrates.com/currency/{code}"

# Banks whose data is excluded due to unreliable / significantly delayed rates.
# Multiple spellings (with / without diacritics) are listed for robustness.
EXCLUDED_BANKS = {
    "بنك الشركة المصرفية العربية الدولية",
    "بنك التعمير والإسكان",
    "مصرف أبوظبى الإسلامى",
    "مصرف أبوظبي الإسلامي",
    "البنك المصرى الخليجى",
    "البنك المصري الخليجي",
    "ميد بنك",
    "المصرف المتحد",
}

# Static fallback rates keyed by currency code.
# Used as a last resort when the live scrape and cache both fail.
# Values are approximate and should be updated periodically.
FALLBACK_RATES = {
    "USD": [
        {"currency": "USD", "buy": 51.69, "sell": 51.79, "bank": "البنك الأهلي المصري"},
        {"currency": "USD", "buy": 51.64, "sell": 51.74, "bank": "البنك التجاري الدولي (CIB)"},
        {"currency": "USD", "buy": 51.69, "sell": 51.79, "bank": "بنك مصر"},
    ],
    "EUR": [
        {"currency": "EUR", "buy": 58.50, "sell": 58.70, "bank": "البنك الأهلي المصري"},
        {"currency": "EUR", "buy": 58.45, "sell": 58.65, "bank": "البنك التجاري الدولي (CIB)"},
    ],
    "SAR": [{"currency": "SAR", "buy": 13.78, "sell": 13.82, "bank": "البنك الأهلي المصري"}],
    "AED": [{"currency": "AED", "buy": 14.07, "sell": 14.12, "bank": "البنك الأهلي المصري"}],
    "GBP": [{"currency": "GBP", "buy": 68.50, "sell": 68.80, "bank": "البنك الأهلي المصري"}],
    "KWD": [{"currency": "KWD", "buy": 168.20, "sell": 168.90, "bank": "البنك الأهلي المصري"}],
    "QAR": [{"currency": "QAR", "buy": 14.10, "sell": 14.22, "bank": "البنك الأهلي المصري"}],
    "AUD": [{"currency": "AUD", "buy": 33.40, "sell": 33.65, "bank": "البنك الأهلي المصري"}],
    "CAD": [{"currency": "CAD", "buy": 36.80, "sell": 37.10, "bank": "البنك الأهلي المصري"}],
    "JPY": [{"currency": "JPY", "buy": 0.334, "sell": 0.338, "bank": "البنك الأهلي المصري"}],
    "CNY": [{"currency": "CNY", "buy": 7.15, "sell": 7.25, "bank": "البنك الأهلي المصري"}],
    "OMR": [{"currency": "OMR", "buy": 134.20, "sell": 135.10, "bank": "البنك الأهلي المصري"}],
}


def _parse_float(text: str) -> float | None:
    """Safely extract a float from text."""
    try:
        cleaned = re.sub(r"[^\d.]", "", text.strip())
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


# ── Provider ─────────────────────────────────────────────────────────────────

class EgratesProvider(BaseProvider):
    """Scrapes egrates.com per-currency pages for multi-bank buy/sell rates.

    Each call to ``_fetch_live`` targets a single currency code. The caller
    (currency engine) invokes this once per currency and aggregates results.
    """

    @property
    def name(self) -> str:
        return "egrates"

    def _fetch_live(self, **kwargs) -> list[dict]:
        """Scrape buy/sell rates for a single currency from egrates.com.

        Keyword Args:
            currency (str): ISO 4217 code to scrape (default ``"USD"``).

        Returns:
            List of dicts, one per bank, with keys:
            currency, buy, sell, bank, source, timestamp.
            Returns an empty list if the page has no rate table.
        """
        code = kwargs.get("currency", "USD")
        url = BASE_URL.format(code=code.lower())

        resp = self._http_get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        now = datetime.now(timezone.utc).isoformat()
        results = []

        # The page contains a single <table> listing all banks for this currency.
        table = soup.find("table")
        if not table:
            return []  # Page layout may have changed or currency not listed.

        # Iterate over every <tr>: col-0 = bank name, col-1 = buy, col-2 = sell.
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue  # Skip header or malformed rows.

            bank_name = cells[0].get_text(strip=True)
            if bank_name in EXCLUDED_BANKS:
                continue  # Skip banks known to report unreliable data.

            # Buy rate extraction — three-tier strategy to handle layout variants:
            #   1. <i data-value="..."> attribute (highest fidelity, machine-readable)
            #   2. <a> tag inner text (sometimes used for linked rates)
            #   3. Raw cell text (last resort)
            buy_val = None
            buy_icon = cells[1].find("i", attrs={"data-value": True})
            if buy_icon:
                buy_val = _parse_float(buy_icon["data-value"])
            if buy_val is None:
                buy_a = cells[1].find("a")
                buy_val = _parse_float(buy_a.text) if buy_a else None
            if buy_val is None:
                buy_val = _parse_float(cells[1].get_text())

            # Sell rate extraction — same three-tier strategy as buy.
            sell_val = None
            sell_icon = cells[2].find("i", attrs={"data-value": True})
            if sell_icon:
                sell_val = _parse_float(sell_icon["data-value"])
            if sell_val is None:
                sell_a = cells[2].find("a")
                sell_val = _parse_float(sell_a.text) if sell_a else None
            if sell_val is None:
                sell_val = _parse_float(cells[2].get_text())

            # Discard row if either rate could not be parsed.
            if buy_val is None or sell_val is None:
                continue

            results.append({
                "currency": code,
                "buy": buy_val,
                "sell": sell_val,
                "bank": bank_name,
                "source": self.name,
                "timestamp": now,
            })

        return results

    def _get_fallback(self, **kwargs) -> list[dict]:
        """Return hardcoded static rates for the requested currency.

        These are approximate values used only when both the live scrape
        and the last-known-good cache are unavailable.
        """
        code = kwargs.get("currency", "USD")
        now = datetime.now(timezone.utc).isoformat()
        return [
            {**r, "source": self.name, "timestamp": now}
            for r in FALLBACK_RATES.get(code, [])
        ]
