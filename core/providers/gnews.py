# ============================================================
# CORE/PROVIDERS/GNEWS.PY — GNews news provider
# ============================================================
import logging
from datetime import datetime, timezone

import requests

from core.providers.base import NewsProvider, ProviderResult, make_content_hash

log = logging.getLogger(__name__)

BASE_URL = "https://gnews.io/api/v4/search"
LIMITATIONS = "Free tier: 100 requests/day, 10 results max. Article count is not market demand."


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


class GNewsProvider(NewsProvider):

    @property
    def name(self) -> str:
        return "gnews"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("GNewsProvider requires 'api_key'")
        self.max_results = int(config.get("limit", 10))

    def search_news(self, query, geography=None, limit=10) -> list:
        if not self.enabled:
            return []
        if geography:
            query = f"{query} {geography}"

        params = {
            "q": query,
            "lang": "en",
            "max": max(1, min(limit, self.max_results, 10)),
            "apikey": self.api_key,
        }

        try:
            resp = requests.get(BASE_URL, params=params, timeout=8)
        except Exception as e:
            # log the exception type only — the URL contains the API key
            log.error("GNews request failed: %s", type(e).__name__)
            return []

        if resp.status_code != 200:
            log.error("GNews returned HTTP %s", resp.status_code)
            return []

        try:
            articles = resp.json().get("articles") or []
        except Exception:
            log.error("GNews returned invalid JSON")
            return []

        results = []
        for article in articles:
            try:
                results.append(self._normalize(article, geography))
            except Exception as e:
                log.warning("GNews: skipped malformed article (%s)", type(e).__name__)
        return results

    def _normalize(self, article: dict, geography) -> ProviderResult:
        url = article["url"]
        snippet = article.get("description") or ""
        source = (article.get("source") or {}).get("name", "unknown")
        content_hash = make_content_hash(url, snippet)

        raw = dict(article)
        raw["content_hash"] = content_hash

        return ProviderResult(
            title=article.get("title", ""),
            url=url,
            snippet=snippet,
            source_name=f"GNews / {source}",
            source_type="news",
            retrieved_at=datetime.now(timezone.utc),
            published_at=_parse_date(article.get("publishedAt")),
            geography=geography,
            topic=None,
            limitations=LIMITATIONS,
            raw=raw,
        )