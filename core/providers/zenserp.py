# ============================================================
# CORE/PROVIDERS/ZENSERP.PY — Zenserp search provider
# Verify current free-tier limits and the response shape at
# zenserp.com before relying on this in production.
# ============================================================
import logging
from datetime import datetime, timezone

import requests

from core.providers.base import SearchProvider, ProviderResult, make_content_hash

log = logging.getLogger(__name__)

BASE_URL = "https://app.zenserp.com/api/v2/search"
LIMITATIONS = "Search rank is not market share. Free-tier quota is limited."


class ZenserpProvider(SearchProvider):

    @property
    def name(self) -> str:
        return "zenserp"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("ZenserpProvider requires 'api_key'")
        self.max_results = int(config.get("limit", 10))

    def search(self, query, geography=None, limit=10) -> list:
        if not self.enabled:
            return []
        if geography:
            query = f"{query} {geography}"

        params = {"q": query, "num": max(1, min(limit, self.max_results))}
        # API key goes in the header so it never appears in URLs or logs
        headers = {"apikey": self.api_key}

        try:
            resp = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        except Exception as e:
            log.error("Zenserp request failed: %s", type(e).__name__)
            return []

        if resp.status_code == 429:
            log.warning("Zenserp quota or rate limit hit")
            return []
        if resp.status_code != 200:
            log.error("Zenserp returned HTTP %s", resp.status_code)
            return []

        try:
            organic = resp.json().get("organic") or []
        except Exception:
            log.error("Zenserp returned invalid JSON")
            return []

        results = []
        for item in organic[:limit]:
            normalized = self._normalize(item, geography)
            if normalized is not None:
                results.append(normalized)
        return results

    def _normalize(self, item: dict, geography):
        url = item.get("url") or ""
        if not url:
            return None
        snippet = item.get("description") or ""
        content_hash = make_content_hash(url, snippet)

        raw = dict(item)
        raw["content_hash"] = content_hash

        return ProviderResult(
            title=item.get("title", ""),
            url=url,
            snippet=snippet,
            source_name="Zenserp / Google",
            source_type="search",
            retrieved_at=datetime.now(timezone.utc),
            published_at=None,
            geography=geography,
            topic=None,
            limitations=LIMITATIONS,
            raw=raw,
        )