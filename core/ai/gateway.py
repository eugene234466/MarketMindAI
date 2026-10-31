# ============================================================
# CORE/AI/GATEWAY.PY — Task routing, retries, validation, usage log
# ============================================================
import logging
import os
import time

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
BACKOFF_SECONDS = [2, 5]

# Override via env vars. Verify model names against Groq's current model list.
MODEL_FAST = os.getenv("GROQ_MODEL_FAST", "llama-3.1-8b-instant")
MODEL_MAIN = os.getenv("GROQ_MODEL_MAIN", "llama-3.3-70b-versatile")

# task -> provider + model. Adding Gemini later = new provider class + edits here.
ROUTES = {
    "summary":    {"provider": "groq", "model": MODEL_FAST},
    "extraction": {"provider": "groq", "model": MODEL_MAIN},
    "analysis":   {"provider": "groq", "model": MODEL_MAIN},
    "report":     {"provider": "groq", "model": MODEL_MAIN},
}

_providers = {}


def register_ai_provider(provider):
    _providers[provider.name] = provider
    log.info("Registered AI provider: %s", provider.name)


def _log_usage(result, task, status, user_id, analysis_id):
    try:
        from database.db import log_ai_usage
        log_ai_usage(result, task, status, user_id, analysis_id)
    except Exception as e:
        # usage tracking must never break an analysis
        log.warning("AI usage logging failed: %s", type(e).__name__)


def run_task(task, messages, response_schema=None, validator=None,
             user_id=None, analysis_id=None):
    """
    Returns an AIResult on success, or None when every attempt failed.
    Callers already have fallbacks, so None means "use the fallback".

    response_schema: pass True (or any non-None value) to request JSON parsing.
    validator: optional function(parsed) -> bool, e.g. checks required keys.
    """
    route = ROUTES.get(task) or ROUTES["analysis"]
    provider = _providers.get(route["provider"])
    if provider is None:
        log.error("No AI provider registered for '%s'", route["provider"])
        return None

    for attempt in range(MAX_ATTEMPTS):
        result = provider.generate(task, messages, response_schema, route["model"])

        if not result.ok:
            status = "error"
        elif response_schema is not None:
            if result.parsed is None:
                status = "invalid"
            elif validator is not None:
                try:
                    status = "ok" if validator(result.parsed) else "invalid"
                except Exception:
                    status = "invalid"
            else:
                status = "ok"
        else:
            status = "ok"

        _log_usage(result, task, status, user_id, analysis_id)

        if status == "ok":
            return result

        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])

    return None