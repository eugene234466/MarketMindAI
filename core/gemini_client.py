# ============================================================
# CORE/GEMINI_CLIENT.PY — Gemini AI Integration
# ============================================================

import time
import json
import hashlib
from threading import Lock
from config import Config

try:
    from google import genai

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    GEMINI_AVAILABLE = bool(Config.GEMINI_API_KEY)

    if GEMINI_AVAILABLE:
        print("Gemini client initialized")

except Exception as e:
    print(f"Gemini init failed: {e}")
    GEMINI_AVAILABLE = False
    client = None


# ─────────────────────────────
# CACHE
# ─────────────────────────────

_cache = {}
_cache_lock = Lock()


def _cache_key(prompt):
    return hashlib.md5(prompt.encode()).hexdigest()


def _get_cached(prompt):
    with _cache_lock:
        return _cache.get(_cache_key(prompt))


def _set_cached(prompt, result):

    with _cache_lock:

        if len(_cache) >= 100:
            _cache.pop(next(iter(_cache)))

        _cache[_cache_key(prompt)] = result


# ─────────────────────────────
# GEMINI CALL
# ─────────────────────────────

def call_gemini(prompt, retries=3):

    cached = _get_cached(prompt)
    if cached:
        print("Gemini cache hit")
        return cached

    if not GEMINI_AVAILABLE:
        return None

    model = getattr(Config, "GEMINI_MODEL", "gemini-2.0-flash")

    for attempt in range(retries):

        try:

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            result = response.text
            _set_cached(prompt, result)
            return result

        except Exception as e:

            error = str(e)

            if "429" in error or "RESOURCE_EXHAUSTED" in error:

                wait = 2 ** attempt * 5
                print(f"Gemini rate limit — waiting {wait}s")

                time.sleep(wait)

            else:

                print(f"Gemini error: {e}")
                return None

    print("Gemini max retries reached")
    return None


# ─────────────────────────────
# ANALYZE IDEA
# ─────────────────────────────

def analyze_idea(idea):

    print(f'Gemini analyzing: "{idea}"')

    prompt = f"""
You are a professional business analyst.

Analyze this business idea:

{idea}

Respond ONLY with valid JSON:

{{
    "summary": "2-3 sentence overview of the opportunity",
    "target_market": "who the ideal customers are",
    "verdict": "GO",
    "verdict_reason": "short reason for the verdict",
    "recommendations": [
        "recommendation 1",
        "recommendation 2",
        "recommendation 3",
        "recommendation 4",
        "recommendation 5"
    ],
    "key_risks": [
        "risk 1",
        "risk 2",
        "risk 3"
    ],
    "pricing": {{
        "budget": "$X - $Y",
        "mid": "$X - $Y",
        "premium": "$X - $Y"
    }},
    "competition_level": "Medium",
    "profit_potential": "High",
    "market_size": "Large"
}}
"""

    result = call_gemini(prompt)

    if not result:
        return None

    try:
        return json.loads(result)

    except Exception as e:
        print(f"JSON parse error: {e}")
        return None
