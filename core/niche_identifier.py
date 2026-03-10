# ============================================================
# CORE/NICHE_IDENTIFIER.PY — Niche Opportunities
# Uses Gemini only (1 call) + caching
# Zero SerpAPI calls
# ============================================================

import json
import hashlib
from core.gemini_client import call_gemini

# ── IN-MEMORY CACHE ──────────────────────────────────────────
_niche_cache = {}

def _cache_key(idea):
    return hashlib.md5(idea.strip().lower().encode()).hexdigest()


# ── MAIN FUNCTION ────────────────────────────────────────────
def identify_niches(idea, market_data=None):
    print(f"Identifying niches for: {idea}")

    # ── CHECK CACHE ──────────────────────────────────────────
    key = _cache_key(idea)
    if key in _niche_cache:
        print("Niche cache hit")
        return _niche_cache[key]

    # ── GET NICHES FROM GEMINI ────────────────────────────────
    niches = get_ai_niches(idea, market_data)

    # ── STORE IN CACHE ────────────────────────────────────────
    if len(_niche_cache) >= 50:
        del _niche_cache[next(iter(_niche_cache))]
    _niche_cache[key] = niches

    print(f"Found {len(niches)} niche opportunities")
    return niches


# ── GEMINI NICHE ANALYSIS (1 CALL) ───────────────────────────
def get_ai_niches(idea, market_data=None):
    competition = "Medium"
    if market_data:
        competition = market_data.get("competition_level", "Medium")

    prompt = f"""
    Identify 5 profitable niche opportunities for: "{idea}"
    Current market competition level: {competition}

    Focus on underserved segments with high profit potential.

    Respond ONLY with valid JSON array, no markdown:
    [
        {{
            "name"       : "Niche Name",
            "score"      : 85,
            "description": "Why this niche is profitable and underserved",
            "audience"   : "Target audience description",
            "entry_cost" : "Low" or "Medium" or "High"
        }}
    ]

    Score each niche 1-100 based on:
    - Market demand (30%)
    - Competition level (25%)
    - Profit margin (25%)
    - Entry barrier (20%)
    """

    result = call_gemini(prompt)

    if result:
        try:
            clean = result.strip()
            if "```" in clean:
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            niches = json.loads(clean.strip())

            # ── VALIDATE & CLAMP SCORES ───────────────────────
            for niche in niches:
                niche["score"] = max(1, min(100, int(niche.get("score", 50))))

            return niches[:5]

        except Exception as e:
            print(f"Niche parse error: {e}")

    return _fallback_niches(idea)


# ── FALLBACK ─────────────────────────────────────────────────
def _fallback_niches(idea):
    return [
        {
            "name"       : f"Budget {idea}",
            "score"      : 72,
            "description": "Price-conscious consumers looking for value",
            "audience"   : "Students and young professionals",
            "entry_cost" : "Low"
        },
        {
            "name"       : f"Premium {idea}",
            "score"      : 65,
            "description": "High-end segment willing to pay for quality",
            "audience"   : "Professionals and enthusiasts",
            "entry_cost" : "Medium"
        },
        {
            "name"       : f"Local {idea}",
            "score"      : 80,
            "description": "Locally-focused with community appeal",
            "audience"   : "Local market and diaspora",
            "entry_cost" : "Low"
        }
    ]
