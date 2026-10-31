# ============================================================
# CORE/PROVIDERS/BASE.PY — Provider interfaces + normalized result
# ============================================================
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def make_content_hash(url: str, snippet: str) -> str:
    """Stable fingerprint used to deduplicate evidence."""
    return hashlib.md5(((url or "") + (snippet or "")).encode("utf-8")).hexdigest()


@dataclass
class ProviderResult:
    # What was found
    title: str
    url: str
    snippet: str

    # Where it came from
    source_name: str
    source_type: str  # "search" | "news" | "company" | "geographic" | "research"
    retrieved_at: datetime

    # Optional context
    published_at: Optional[datetime] = None
    geography: Optional[str] = None
    topic: Optional[str] = None
    limitations: Optional[str] = None

    # Original response + content_hash, kept for debugging and dedup
    raw: dict = field(default_factory=dict)

    @property
    def content_hash(self) -> Optional[str]:
        return self.raw.get("content_hash")


class BaseProvider(ABC):
    def __init__(self, config: dict):
        if not isinstance(config, dict):
            raise ValueError("Provider config must be a dict")
        self.config = config
        self._enabled = bool(config.get("enabled", True))

    @property
    @abstractmethod
    def name(self) -> str:
        """Short provider id, e.g. 'gnews'."""

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _check_enabled(self):
        if not self.enabled:
            raise RuntimeError(f"Provider '{self.name}' is disabled")


class SearchProvider(BaseProvider):
    @abstractmethod
    def search(self, query: str, geography: Optional[str] = None,
               limit: int = 10) -> list:
        """Return list[ProviderResult]. Must never raise to the caller."""


class NewsProvider(BaseProvider):
    @abstractmethod
    def search_news(self, query: str, geography: Optional[str] = None,
                    limit: int = 10) -> list:
        """Return list[ProviderResult]. Must never raise to the caller."""


class CompanyDataProvider(BaseProvider):
    @abstractmethod
    def search_companies(self, query: str, geography: Optional[str] = None,
                         limit: int = 10) -> list:
        pass


class GeographicProvider(BaseProvider):
    @abstractmethod
    def search_places(self, query: str, geography: Optional[str] = None) -> list:
        pass


class WebsiteExtractionProvider(BaseProvider):
    @abstractmethod
    def extract(self, url: str) -> Optional[ProviderResult]:
        """Validate the URL (SSRF protection) before fetching."""