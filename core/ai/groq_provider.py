# ============================================================
# CORE/AI/GROQ_PROVIDER.PY — Groq behind the AIProvider interface
# ============================================================
import logging
import time

from core.ai.base import AIProvider, AIResult, parse_json_loose

log = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(AIProvider):

    @property
    def name(self) -> str:
        return "groq"

    def __init__(self, config: dict):
        super().__init__(config)
        from groq import Groq
        self._client = Groq(api_key=self.api_key, timeout=self.timeout)

    def generate(self, task, messages, response_schema=None, model=None) -> AIResult:
        model = model or self.default_model or DEFAULT_MODEL
        started = time.time()

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.4,
                max_tokens=1500,
            )
        except Exception as e:
            # Log the exception type only. Never log messages: they contain user ideas.
            log.error("Groq call failed (task=%s): %s", task, type(e).__name__)
            return AIResult(
                ok=False, provider=self.name, model=model,
                duration_ms=int((time.time() - started) * 1000),
            )

        try:
            text = response.choices[0].message.content or ""
        except Exception:
            text = ""

        usage = getattr(response, "usage", None)
        parsed = parse_json_loose(text) if response_schema is not None else None

        return AIResult(
            ok=bool(text),
            text=text,
            parsed=parsed,
            provider=self.name,
            model=model,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            duration_ms=int((time.time() - started) * 1000),
        )