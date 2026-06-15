"""
Google News RSS provider for business news fallback.

Data source:
    Google News public RSS endpoint filtered for "business Egypt" in English.
    URL: ``https://news.google.com/rss/search?q=business+Egypt&hl=en-US&gl=US&ceid=US:en``

Parsing:
    Uses the ``feedparser`` library to parse the RSS XML.  Each ``<item>``
    becomes a dict with title, url, published_at, image (always empty for
    RSS), and source.

Role in the system:
    This provider acts as the **secondary fallback** for news.  The news
    engine first tries NewsAPI; if that fails, it falls back to this
    Google News RSS scraper before resorting to static placeholder articles.
"""

import feedparser
from services.core.base_provider import BaseProvider

class GoogleNewsProvider(BaseProvider):
    """Fetches recent Egypt-related business headlines via Google News RSS.

    No API key is required — the endpoint is public.  However, Google may
    throttle or block requests if called too frequently.
    """
    @property
    def name(self) -> str:
        return "google_news"

    def _fetch_live(self, **kwargs) -> list[dict]:
        """Parse the Google News RSS feed and return article metadata.

        Returns:
            List of dicts with keys: title, url, published_at, image, source.

        Raises:
            Exception: If ``feedparser`` flags the feed as malformed (bozo=1).
        """
        # Google News RSS for Egypt Business
        url = "https://news.google.com/rss/search?q=business+Egypt&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        
        # feedparser sets bozo=1 when the feed is malformed or unreachable.
        if getattr(feed, "bozo", 0) == 1:
            raise Exception(f"Failed to parse Google News RSS: {getattr(feed, 'bozo_exception', 'Unknown error')}")
            
        results = []
        for entry in feed.entries:
            results.append({
                "title": entry.title,
                "url": entry.link,
                "published_at": getattr(entry, "published", ""),
                "image": "",  # RSS feed does not provide thumbnail images.
                "source": "Google News"
            })
        return results

    def _get_fallback(self, **kwargs) -> list[dict]:
        """No static fallback — the news engine handles its own final fallback."""
        return []
