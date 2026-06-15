"""News Engine orchestration."""

import logging
from services.providers.news_api_provider import NewsApiProvider
from services.providers.google_news_provider import GoogleNewsProvider
from services.core.data_normalizer import normalize_news
from services.cache.cache_manager import cache_manager

logger = logging.getLogger(__name__)

def get_latest_news(limit: int = 5, keyword: str = "") -> dict:
    cache_key = f"news_{limit}_{keyword}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        return {"data": cached, "source": "cache"}

    news_api = NewsApiProvider()
    gnews = GoogleNewsProvider()
    
    # Try NewsAPI
    res = news_api.fetch()
    
    # Fallback to Google News
    if not res.success or not res.data:
        logger.warning("NewsAPI failed or returned empty. Falling back to Google News RSS.")
        res = gnews.fetch()

    data = res.data
    
    # Static fallback
    if not res.success or not data:
        logger.warning("Google News failed or returned empty. Using static fallback.")
        data = [
            {
                "title": "Central Bank of Egypt announces new monetary policies to stabilize exchange rate",
                "url": "#",
                "published_at": "",
                "image": "",
                "source": "OptiRate Alerts"
            },
            {
                "title": "Global gold prices see slight dip amidst market corrections and inflation",
                "url": "#",
                "published_at": "",
                "image": "",
                "source": "OptiRate Alerts"
            },
            {
                "title": "Major banks increase deposit interest rates following MPC meeting",
                "url": "#",
                "published_at": "",
                "image": "",
                "source": "OptiRate Alerts"
            }
        ]
        is_fallback = True
        source = "static_fallback"
    else:
        is_fallback = False
        source = res.source

    normalized = []
    for item in data:
        if keyword and keyword.lower() not in item.get("title", "").lower():
            continue
        norm = normalize_news(item, fallback=is_fallback, source=item.get("source", source))
        normalized.append(norm)

    # Apply Limit
    normalized = normalized[:limit]

    # Cache for 300 seconds (5 minutes)
    if normalized:
        cache_manager.set_ttl("news", 300)
        cache_manager.set(cache_key, normalized, domain="news")

    return {"data": normalized, "source": source}
