# ============================================================
# CORE/BOOTSTRAP.PY — Register every configured provider
# Call register_all() once inside create_app().
# ============================================================
import logging
import os

from core.providers.registry import registry
from core.providers.gnews import GNewsProvider
from core.providers.zenserp import ZenserpProvider
from core.ai.gateway import register_ai_provider
from core.ai.groq_provider import GroqProvider

log = logging.getLogger(__name__)


def register_all():
    # ── Research providers ───────────────────────────────────
    gnews_key = os.getenv("GNEWS_API_KEY", "")
    if gnews_key:
        registry.register(GNewsProvider({"api_key": gnews_key}))
    else:
        log.warning("GNEWS_API_KEY not set — GNews disabled")

    zenserp_key = os.getenv("ZENSERP_API_KEY", "")
    if zenserp_key:
        registry.register(ZenserpProvider({"api_key": zenserp_key}))
    else:
        log.warning("ZENSERP_API_KEY not set — Zenserp disabled")

    # ── AI providers ─────────────────────────────────────────
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        register_ai_provider(GroqProvider({"api_key": groq_key, "timeout": 30}))
    else:
        log.warning("GROQ_API_KEY not set — AI disabled")