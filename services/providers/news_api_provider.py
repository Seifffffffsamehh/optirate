"""
NewsAPI provider for live business news.

Data source:
    ``https://newsapi.org/v2/top-headlines`` — returns Egyptian business
    headlines using the ``country=eg&category=business`` query parameters.

Authentication:
    Requires a ``NEWS_API_KEY`` environment variable.  If the key is missing,
    the provider raises immediately so the news engine can fall back to
    the Google News RSS provider.

Role in the system:
    This is the **primary** news provider.  The news engine tries this first;
    on failure it falls back to Google News RSS, and finally to static
    placeholder articles.
"""

import os
from services.core.base_provider import BaseProvider

class NewsApiProvider(BaseProvider):
    """Fetches Egyptian business headlines from the NewsAPI REST endpoint.

    Requires the ``NEWS_API_KEY`` environment variable to be set.
    """
    @property
    def name(self) -> str:
        return "news_api"

    def _fetch_live(self, **kwargs) -> list[dict]:
        """Call the NewsAPI top-headlines endpoint for Egyptian business news.

        Returns:
            List of dicts with keys: title, url, published_at, image, source.

        Raises:
            Exception: If the API key is missing or the API returns an error.
        """
        # Expecting key in environment, defaulting to empty for failover simulation
        api_key = os.environ.get("NEWS_API_KEY", "")
        if not api_key:
            raise Exception("NewsAPI Key missing, triggering fallback.")
            
        # Build the request URL with the API key as a query parameter.
        url = f"https://newsapi.org/v2/top-headlines?country=eg&category=business&apiKey={api_key}"
        resp = self._http_get(url)
        resp.raise_for_status()
        
        # Validate that the API responded with a success status.
        data = resp.json()
        if data.get("status") != "ok":
            raise Exception(f"NewsAPI returned error status: {data.get('message')}")
            
        # Transform each article into the normalised schema expected by the news engine.
        articles = data.get("articles", [])
        results = []
        for a in articles:
            results.append({
                "title": a.get("title"),
                "url": a.get("url"),
                "published_at": a.get("publishedAt"),
                "image": a.get("urlToImage"),
                "source": a.get("source", {}).get("name", "NewsAPI")
            })
        return results

    def _get_fallback(self, **kwargs) -> list[dict]:
        """No static fallback — the news engine manages its own final fallback."""
        return []
