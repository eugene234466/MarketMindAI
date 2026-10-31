# ============================================================
# CORE/AI/BASE.PY — AI provider interface + JSON helper
# ============================================================
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class AIResult:
    ok: bool
    text: str = ""
    parsed: Any = None                  # dict / list after JSON parsing, or None
    provider: str = ""
    model: str = ""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    duration_ms: int = 0


class AIProvider(ABC):
    def __init__(self, config: dict):
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("AI provider requires 'api_key'")
        self.default_model = config.get("default_model")
        self.timeout = config.get("timeout", 30)

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider id, e.g. 'groq'."""

    @abstractmethod
    def generate(self, task, messages, response_schema=None, model=None) -> AIResult:
        """Must NEVER raise. Return AIResult(ok=False) on any failure."""


def parse_json_loose(text):
    """Parse JSON from model output, tolerating ``` fences and stray prose."""
    if not text:
        return None
    clean = text.strip()

    if "```" in clean:
        for part in clean.split("```"):
            part = part.strip()
            if part.lower().startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") or part.startswith("["):
                clean = part
                break

    try:
        return json.loads(clean)
    except Exception:
        pass

    # Fallback: slice from the first opener to its matching last closer.
    # Try whichever opener appears first, so [{...}] isn't mistaken for {...}.
    candidates = []
    for opener, closer in (("{", "}"), ("[", "]")):
        start = clean.find(opener)
        end = clean.rfind(closer)
        if start != -1 and end > start:
            candidates.append((start, end))
    for start, end in sorted(candidates):
        try:
            return json.loads(clean[start:end + 1])
        except Exception:
            continue
    return None