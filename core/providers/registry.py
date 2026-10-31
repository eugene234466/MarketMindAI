# ============================================================
# CORE/PROVIDERS/REGISTRY.PY — One place to find providers
# ============================================================
import logging
from typing import Optional

from core.providers.base import BaseProvider

log = logging.getLogger(__name__)


class ProviderRegistry:
    def __init__(self):
        self._providers = {}

    def register(self, provider: BaseProvider):
        self._providers[provider.name] = provider
        log.info("Registered provider: %s", provider.name)

    def get(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    def get_all(self, provider_type: type) -> list:
        """All ENABLED providers that are instances of provider_type."""
        return [
            p for p in self._providers.values()
            if isinstance(p, provider_type) and p.enabled
        ]

    def list_registered(self) -> list:
        return list(self._providers.keys())


# One global registry for the whole app
registry = ProviderRegistry()