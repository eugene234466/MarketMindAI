# IMPORTS
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

# ── NORMALIZED RESULT ─────────────────────────────────────────
# Every provider returns this — no matter the source
@dataclass
class ProviderResult:
    # What was found
    title: str
    url: str
    snippet: str

    # Where it came from
    source_name: str
    source_type: str        # "search" | "news" | "company" | "geographic" | "research"

    # When
    retrieved_at: datetime
    published_at: Optional[datetime]

    # Context
    geography: Optional[str]
    topic: Optional[str]

    # Reliability
    limitations: Optional[str]

    # Raw original response stored for debugging
    raw: Optional[dict] = field(default_factory=dict)


# ── BASE PROVIDER ─────────────────────────────────────────────
# All providers inherit from this
class BaseProvider(ABC):

    def __init__(self, config: dict):
        # Store config (api_key, limits, enabled flag etc)
        # Raise ValueError if required keys are missing
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        # Return provider name e.g. "zenserp" "gnews" "openstreetmap"
        pass

    @property
    def enabled(self) -> bool:
        # Check config for enabled flag
        # Return True by default
        pass

    def _check_enabled(self):
        # If not enabled raise a RuntimeError with a clear message
        pass


# ── SEARCH PROVIDER ───────────────────────────────────────────
class SearchProvider(BaseProvider):

    @abstractmethod
    def search(
        self,
        query: str,
        geography: Optional[str] = None,
        limit: int = 10
    ) -> list[ProviderResult]:
        # Subclasses implement this
        # Must return list of ProviderResult
        # Must handle timeouts and HTTP errors — never raise to caller
        # Must respect limit
        pass


# ── NEWS PROVIDER ─────────────────────────────────────────────
class NewsProvider(BaseProvider):

    @abstractmethod
    def search_news(
        self,
        query: str,
        geography: Optional[str] = None,
        limit: int = 10
    ) -> list[ProviderResult]:
        pass


# ── COMPANY DATA PROVIDER ─────────────────────────────────────
class CompanyDataProvider(BaseProvider):

    @abstractmethod
    def search_companies(
        self,
        query: str,
        geography: Optional[str] = None,
        limit: int = 10
    ) -> list[ProviderResult]:
        pass


# ── GEOGRAPHIC PROVIDER ───────────────────────────────────────
class GeographicProvider(BaseProvider):

    @abstractmethod
    def search_places(
        self,
        query: str,
        geography: Optional[str] = None
    ) -> list[ProviderResult]:
        pass


# ── WEBSITE EXTRACTION PROVIDER ───────────────────────────────
class WebsiteExtractionProvider(BaseProvider):

    @abstractmethod
    def extract(self, url: str) -> Optional[ProviderResult]:
        # Extract title, description, text from a URL
        # Must validate URL before fetching (SSRF protection goes here)
        pass
