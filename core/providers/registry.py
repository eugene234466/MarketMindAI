# IMPORTS
from core.providers.base import BaseProvider, SearchProvider, NewsProvider

# ── REGISTRY ──────────────────────────────────────────────────
# Single place to register and look up all providers
class ProviderRegistry:

    def __init__(self):
        # _providers: dict mapping name -> BaseProvider instance
        # e.g. {"zenserp": ZenserpProvider, "gnews": GNewsProvider}
        pass

    def register(self, provider: BaseProvider):
        # Add provider to _providers by its name
        # Log registration
        pass

    def get(self, name: str) -> Optional[BaseProvider]:
        # Return provider by name
        # Return None if not found — do not raise
        pass

    def get_all(self, provider_type: type) -> list[BaseProvider]:
        # Return all registered providers of a given type
        # e.g. get_all(SearchProvider) returns all search providers
        # Only return enabled ones
        pass

    def list_registered(self) -> list[str]:
        # Return list of all registered provider names
        pass


# ── SINGLETON ─────────────────────────────────────────────────
# One global registry used throughout the app
registry = ProviderRegistry()
