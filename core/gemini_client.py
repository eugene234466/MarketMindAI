# ============================================================
# CORE/GEMINI_CLIENT.PY — Gemini AI Integration
# Uses google-genai (2026) with retry + caching
# Clean fallback messages — no API key mentions
# ============================================================

import time
import json
import hashlib
from config import Config

# ── IMPORT NEW PACKAGE ───────────────────────────────────────
try:
    from google import genai
    client           = genai.Client(api_key=Config.GEMINI_API_KEY)
    GEMINI_AVAILABLE = bool(Config.GEMINI_API_KEY)
    if GEMINI_AVAILABLE:
        print("Gemini client initialized successfully")
except Exception as e:
    print(f"Gemini init failed: {e}")
    GEMINI_AVAILABLE = False
    client           = None


# ── IN-MEMORY CACHE ──────────────────────────────────────────
_gemini_cache = {}

def _cache_key(prompt):
    return hashlib.md5(prompt.encode()).hexdigest()

def _get_cached(prompt):
    return _gemini_cache.get(_cache_key(prompt))

def _set_cached(prompt, result):
    if len(_gemini_cache) >= 100:
        del _gemini_cache[next(iter(_gemini_cache))]
    _gemini_cache[_cache_key(prompt)] = result


# ── GEMINI CALL WITH RETRY ───────────────────────────────────
def call_gemini(prompt, retries=2):
    cached = _get_cached(prompt)
    if cached:
        print("Gemini cache hit")
        return cached

    if not GEMINI_AVAILABLE or not client:
        return None

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model    = "gemini-2.0-flash",
                contents = prompt
            )
            result = response.text
            _set_cached(prompt, result)
            return result

        except Exception as e:
            error = str(e)
            if "429" in error or "RESOURCE_EXHAUSTED" in error:
                wait = (attempt + 1) * 5
                print(f"Gemini rate limit — waiting {wait}s "
                      f"(attempt {attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                print(f"Gemini error: {e}")
                return None

    print("Gemini max retries reached")
    return None


# ── PARSE JSON RESPONSE ──────────────────────────────────────
def _parse_json(text):
    if not text:
        return None
    try:
        clean = text.strip()
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{") or part.startswith("["):
                    clean = part
                    break
        return json.loads(clean.strip())
    except Exception as e:
        print(f"JSON parse error: {e}")
        return None


# ── ANALYZE IDEA ─────────────────────────────────────────────
def analyze_idea(idea):
    print(f'Gemini analyzing: "{idea}"')

    prompt = f"""
    You are a business analyst. Analyze this business idea: "{idea}"

    Provide a thorough, realistic analysis.

    Respond ONLY with valid JSON, no markdown, no backticks:
    {{
        "summary"          : "2-3 sentence market overview and opportunity",
        "target_market"    : "specific target audience description",
        "verdict"          : "GO",
        "verdict_reason"   : "one clear sentence explaining the verdict",
        "recommendations"  : [
            "specific actionable recommendation 1",
            "specific actionable recommendation 2",
            "specific actionable recommendation 3",
            "specific actionable recommendation 4",
            "specific actionable recommendation 5"
        ],
        "key_risks"        : [
            "specific risk 1",
            "specific risk 2",
            "specific risk 3"
        ],
        "pricing"          : {{
            "budget"  : "$X - $Y",
            "mid"     : "$X - $Y",
            "premium" : "$X - $Y"
        }},
        "competition_level": "Medium",
        "profit_potential" : "High",
        "market_size"      : "$XB global market"
    }}

    Verdict must be either "GO" or "NO GO" only.
    Competition level must be one of: Low, Medium, High.
    Profit potential must be one of: Low, Medium, High.
    """

    result  = call_gemini(prompt)
    parsed  = _parse_json(result)

    if parsed:
        # ── VALIDATE REQUIRED FIELDS ──────────────────────────
        parsed.setdefault("verdict",          "GO")
        parsed.setdefault("verdict_reason",   "Strong market opportunity identified")
        parsed.setdefault("recommendations",  [])
        parsed.setdefault("key_risks",        [])
        parsed.setdefault("competition_level","Medium")
        parsed.setdefault("profit_potential", "Medium")
        parsed.setdefault("market_size",      "N/A")
        return parsed

    return _fallback_insights(idea)


# ── SMART FALLBACK — no API key mentions ──────────────────────
def _fallback_insights(idea):
    """
    Returns a reasonable generic insight when Gemini is unavailable.
    Does NOT mention API keys or technical errors to the user.
    """
    idea_lower = idea.lower()

    # ── DETECT IDEA TYPE ─────────────────────────────────────
    is_luxury    = any(w in idea_lower for w in ["gucci","louis","prada","luxury","designer"])
    is_food      = any(w in idea_lower for w in ["food","restaurant","cafe","bakery","catering"])
    is_tech      = any(w in idea_lower for w in ["app","software","tech","ai","saas","platform"])
    is_ecommerce = any(w in idea_lower for w in ["shop","store","sell","ecommerce","online"])
    is_fashion   = any(w in idea_lower for w in ["fashion","clothing","wear","shoes","bags","accessories"])

    # ── SMART PRICING ─────────────────────────────────────────
    if is_luxury:
        pricing = {"budget": "$200 - $500", "mid": "$500 - $2,000", "premium": "$2,000+"}
        verdict = "GO"
        verdict_reason = "Luxury goods show strong demand in emerging African markets with growing middle class."
        competition    = "High"
        profit         = "High"
        market_size    = "$380B global luxury market"
        summary        = (
            f"The market for {idea} represents a significant opportunity, "
            f"particularly in urban West African markets where demand for premium "
            f"and luxury goods is growing rapidly among aspirational consumers. "
            f"Authentication and trust are key differentiators in this space."
        )
        recs = [
            "Partner with verified luxury goods authenticators to build trust",
            "Target affluent urban areas in Accra, Lagos and Nairobi first",
            "Offer layaway or instalment plans to broaden your customer base",
            "Build a strong Instagram and social media presence — luxury buyers research online",
            "Consider a consignment model to reduce inventory risk"
        ]
        risks = [
            "High counterfeit risk damages brand reputation",
            "Currency fluctuation affects import costs significantly",
            "Limited customer base in early stages"
        ]
    elif is_food:
        pricing = {"budget": "$5 - $15", "mid": "$15 - $40", "premium": "$40 - $100"}
        verdict = "GO"
        verdict_reason = "Food and beverage businesses have consistent demand with strong repeat customer potential."
        competition    = "High"
        profit         = "Medium"
        market_size    = "$9T global food industry"
        summary        = (
            f"The {idea} market benefits from consistent consumer demand and strong "
            f"repeat purchase behaviour. Success in this space depends on quality, "
            f"location and building a loyal local customer base."
        )
        recs = [
            "Start with a small test location or market stall before scaling",
            "Develop a signature item that creates word-of-mouth marketing",
            "Use social media to showcase food preparation and quality",
            "Build a delivery partnership with Bolt Food or similar platforms",
            "Focus on food hygiene certification to build customer trust"
        ]
        risks = [
            "High competition from established local eateries",
            "Food spoilage and supply chain inconsistency",
            "Location dependency for foot traffic"
        ]
    elif is_tech:
        pricing = {"budget": "Free / Freemium", "mid": "$10 - $50/month", "premium": "$100 - $500/month"}
        verdict = "GO"
        verdict_reason = "Tech and software products have high scalability and low marginal costs once built."
        competition    = "Medium"
        profit         = "High"
        market_size    = "$700B+ global software market"
        summary        = (
            f"The {idea} space presents a high-growth opportunity with the advantage "
            f"of digital distribution and the ability to scale globally from day one. "
            f"Finding a specific underserved niche is key to gaining early traction."
        )
        recs = [
            "Validate the core feature with 10 real users before building",
            "Choose a freemium model to lower the barrier for early adoption",
            "Focus on one specific user persona and problem to start",
            "Build in public — share your progress to attract early users",
            "Prioritise mobile-first design for the African market"
        ]
        risks = [
            "High competition from international tech giants",
            "Long development timelines before revenue",
            "Customer acquisition costs can be high in early stages"
        ]
    elif is_fashion:
        pricing = {"budget": "$20 - $80", "mid": "$80 - $300", "premium": "$300 - $1,000"}
        verdict = "GO"
        verdict_reason = "Fashion and apparel show strong consumer demand especially in urban African markets."
        competition    = "High"
        profit         = "Medium"
        market_size    = "$2.5T global fashion market"
        summary        = (
            f"The {idea} market is large and growing, with social media driving "
            f"rapid trend cycles and creating demand for new styles. Differentiation "
            f"through unique design or a strong brand story is essential."
        )
        recs = [
            "Build a strong visual brand identity on Instagram and TikTok",
            "Start with a small capsule collection to test demand",
            "Partner with local influencers for authentic reach",
            "Offer made-to-order to reduce inventory risk",
            "Consider Afrocentric designs — a growing global trend"
        ]
        risks = [
            "Fast-changing fashion trends require constant new inventory",
            "High competition from fast fashion imports",
            "Returns and sizing issues in online sales"
        ]
    else:
        # Generic fallback
        pricing     = {"budget": "$20 - $60", "mid": "$60 - $200", "premium": "$200 - $500"}
        verdict     = "GO"
        verdict_reason = "Initial market signals suggest viable demand for this idea with the right positioning."
        competition    = "Medium"
        profit         = "Medium"
        market_size    = "Multi-billion dollar addressable market"
        summary        = (
            f"The {idea} market shows promising potential with a clear customer "
            f"need and room for differentiated positioning. Success will depend on "
            f"execution, customer acquisition strategy and building strong brand trust."
        )
        recs = [
            "Start by validating demand with a small pilot before full launch",
            "Identify and deeply understand your top 3 competitors",
            "Focus on one specific customer segment rather than targeting everyone",
            "Build an online presence early — social media and a simple website",
            "Track your unit economics closely from day one"
        ]
        risks = [
            "Market competition may be stronger than anticipated",
            "Customer acquisition costs in early stages",
            "Cash flow management during growth phase"
        ]

    return {
        "summary"          : summary,
        "target_market"    : "Entrepreneurs, consumers and businesses in urban African markets",
        "verdict"          : verdict,
        "verdict_reason"   : verdict_reason,
        "recommendations"  : recs,
        "key_risks"        : risks,
        "pricing"          : pricing,
        "competition_level": competition,
        "profit_potential" : profit,
        "market_size"      : market_size
    }
