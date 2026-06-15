"""
CBE provider — fetches historical exchange rates from the Central Bank of Egypt.

Scraping target:
    https://www.cbe.org.eg/ar/economic-research/statistics/cbe-exchange-rates
    (Arabic-language page listing official daily buy/sell rates for major currencies)

Parsing strategy:
    1. HTTP GET with retry logic (3 attempts, exponential back-off) and a
       realistic browser User-Agent to avoid WAF blocks.
    2. BeautifulSoup parses the first <table> in the response.
    3. Each row maps an Arabic currency name → ISO 4217 code via CURRENCY_NAME_MAP.
    4. The **sell** column (بيع) is used as the primary rate.
    5. Results are validated: USD must be present or the scrape is rejected.

Error handling:
    - Network / HTTP errors raise immediately (no silent fallback).
    - Missing table or insufficient rows raise ValueError.
    - Missing USD rate raises ValueError to prevent incomplete snapshots.
    - _get_fallback() intentionally returns [] — static fallbacks are
      prohibited for CBE to preserve historical data integrity.
"""

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from services.core.base_provider import BaseProvider

# ── Configuration ────────────────────────────────────────────────────────────

# Official CBE exchange-rates page (Arabic). The table layout is locale-specific.
CBE_MAIN_URL = "https://www.cbe.org.eg/ar/economic-research/statistics/cbe-exchange-rates"

# Maps Arabic currency names (as they appear on the CBE page) to ISO 4217 codes.
# Multiple spellings exist because CBE uses inconsistent diacritics / tatweel,
# so every known variant is mapped to the same code.
CURRENCY_NAME_MAP = {
    "دولار أمريكى": "USD", "دولار أمريكي": "USD",
    "يورو": "EUR",
    "جنيــه إسترليـنى": "GBP", "جنيه إسترلينى": "GBP", "جنيه إسترليني": "GBP",
    "ريال سعودي": "SAR", "ريال سعودى": "SAR",
    "درهم إماراتى": "AED", "درهم إماراتي": "AED",
    "دينار كويتي": "KWD", "دينار كويتى": "KWD",
    "ريال قطري": "QAR", "ريال قطرى": "QAR",
    "ريال عماني": "OMR", "ريال عمانى": "OMR",
    "ين ياباني": "JPY", "ين يابانى": "JPY", "١٠٠ ين يابانى": "JPY", "١٠٠ ين ياباني": "JPY",
    "دولار كندي": "CAD", "دولار كنـدى": "CAD", "دولار كندى": "CAD",
    "دولار أسترالي": "AUD", "دولار اســـترالى": "AUD", "دولار أسترالى": "AUD",
    "اليوان الصينى": "CNY", "يوان صيني": "CNY", "اليوان الصيني": "CNY"
}

# Only these currencies are kept from the scrape; others on the page are discarded.
TARGET_CURRENCIES = {"USD", "EUR", "GBP", "SAR", "AED", "KWD", "QAR", "OMR", "CNY", "JPY", "CAD", "AUD"}


def _clean_currency_name(text: str) -> str:
    """Normalize an Arabic currency label for reliable dictionary look-up.

    Removes tatweel (kashida, U+0640) characters and collapses runs of
    whitespace so that the cleaned string matches a CURRENCY_NAME_MAP key.

    Args:
        text: Raw Arabic text extracted from a table cell.

    Returns:
        Cleaned, single-spaced string suitable for look-up.
    """
    # Remove some common zero-width chars or multiple spaces and tatweel
    text = re.sub(r'[\u0640]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_float(text: str) -> float | None:
    """Extract a numeric float from a cell's text, stripping non-numeric chars.

    Args:
        text: Raw cell text that may contain currency symbols or whitespace.

    Returns:
        Parsed float, or None if the text cannot be converted.
    """
    try:
        cleaned = re.sub(r"[^\d.]", "", text.strip())
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


# ── Provider ─────────────────────────────────────────────────────────────────

class CbeProvider(BaseProvider):
    """Fetches exchange rate data from CBE website."""

    @property
    def name(self) -> str:
        return "cbe"

    def _fetch_live(self, **kwargs) -> list[dict]:
        """Scrape the CBE exchange-rates page and return today's rates.

        Uses a requests Session with automatic retries (3 attempts with
        exponential back-off on 5xx errors) and a desktop browser
        User-Agent to minimize the chance of being blocked by the WAF.

        Returns:
            List of dicts with keys: currency, date, rate, source.

        Raises:
            requests.HTTPError: If the CBE page returns a non-2xx status.
            ValueError: If the expected HTML table is missing, has
                insufficient rows, or the critical USD rate is absent.
        """
        import requests
        import logging
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        logger = logging.getLogger(__name__)
        # Configure a resilient session: retry up to 3 times on server errors
        # with exponential back-off (1s, 2s, 4s).
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        session.mount('http://', HTTPAdapter(max_retries=retries))

        # Mimic a real Chrome browser to avoid WAF / bot-detection blocks.
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        }

        try:
            logger.info("Attempting to scrape CBE rates...")
            resp = session.get(CBE_MAIN_URL, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch CBE rates: {e}")
            raise  # Do NOT return fallback, explicitly fail
        finally:
            session.close()

        # Parse the HTML and locate the first <table> containing exchange rates.
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            logger.error("No table found in the CBE HTML response. Structure might have changed or WAF blocked.")
            raise ValueError("No table found in CBE response")

        results = []  # Accumulates validated {currency, date, rate, source} dicts.
        today = datetime.now(timezone.utc).date()

        rows = table.find_all("tr")
        if len(rows) < 2:
            logger.error("CBE table found but has less than 2 rows.")
            raise ValueError("CBE table lacks data rows")

        # Skip the header row; each data row has ≥3 cells: name, buy, sell.
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            # Column 0 = Arabic name, Column 1 = buy (شراء), Column 2 = sell (بيع).
            c_name = _clean_currency_name(cells[0].get_text(strip=True))
            sell_text = cells[2].get_text(strip=True)  # Using sell rate (بيع) as primary

            # Map Arabic name to ISO code; skip if unrecognised or not tracked.
            currency_code = CURRENCY_NAME_MAP.get(c_name)
            if not currency_code or currency_code not in TARGET_CURRENCIES:
                continue

            # Discard rows where the sell rate is unparseable or non-positive.
            rate = _parse_float(sell_text)
            if rate is None or rate <= 0:
                continue

            results.append({
                "currency": currency_code,
                "date": today.isoformat(),
                "rate": rate,
                "source": "CBE"
            })

        logger.info(f"Scraped {len(results)} currencies successfully from CBE at {datetime.now(timezone.utc).isoformat()}.")
        
        # Verify USD exists
        if not any(r["currency"] == "USD" for r in results):
            logger.error("USD rate is missing from scraped results!")
            raise ValueError("USD rate missing from CBE response")
            
        return results

    def _get_fallback(self, **kwargs) -> list[dict]:
        """Return an empty list — static fallbacks are intentionally disabled.

        CBE data feeds into the historical database, so stale/fabricated
        rates would corrupt the time-series used by forecasting models.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.error("Fallback requested but static fallbacks are strictly prohibited!")
        return []  # No static fallback for history — return empty
