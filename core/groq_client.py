# ============================================================
# CORE/GROQ_CLIENT.PY — Thin wrapper over the AI gateway
# Keeps the old call_groq / analyze_idea API so market_researcher,
# niche_identifier and competitor_analyzer need no changes.
# ============================================================
import hashlib

from core.ai.base import parse_json_loose
from core.ai.gateway import run_task

# ── IN-MEMORY CACHE ──────────────────────────────────────────
_groq_cache = {}


def _cache_key(prompt):
    return hashlib.md5(prompt.encode()).hexdigest()


def call_groq(prompt, retries=2):
    """Returns the model's text, or None. `retries` is kept for compatibility;
    the gateway now owns retries and backoff."""
    key = _cache_key(prompt)
    if key in _groq_cache:
        print("Groq cache hit")
        return _groq_cache[key]

    result = run_task("analysis", [{"role": "user", "content": prompt}])
    if result is None:
        return None

    if len(_groq_cache) >= 100:
        del _groq_cache[next(iter(_groq_cache))]
    _groq_cache[key] = result.text
    return result.text


def _parse_json(text):
    return parse_json_loose(text)


# ── ANALYZE IDEA ─────────────────────────────────────────────
def analyze_idea(idea):
    print(f'Groq analyzing: "{idea}"')

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

    parsed = _parse_json(call_groq(prompt))

    if isinstance(parsed, dict):
        parsed.setdefault("verdict",          "GO")
        parsed.setdefault("verdict_reason",   "Strong market opportunity identified")
        parsed.setdefault("recommendations",  [])
        parsed.setdefault("key_risks",        [])
        parsed.setdefault("competition_level", "Medium")
        parsed.setdefault("profit_potential", "Medium")
        parsed.setdefault("market_size",      "N/A")
        return parsed

    return _fallback_insights(idea)


# ── SMART FALLBACK ────────────────────────────────────────────
def _fallback_insights(idea):
    idea_lower = idea.lower()

    is_luxury  = any(w in idea_lower for w in ["gucci", "louis", "prada", "luxury", "designer"])
    is_food    = any(w in idea_lower for w in ["food", "restaurant", "cafe", "bakery", "catering"])
    is_tech    = any(w in idea_lower for w in ["app", "software", "tech", "ai", "saas", "platform"])
    is_fashion = any(w in idea_lower for w in ["fashion", "clothing", "wear", "shoes", "bags", "accessories"])

    if is_luxury:
        pricing = {"budget": "$200 - $500", "mid": "$500 - $2,000", "premium": "$2,000+"}
        verdict_reason = "Luxury goods show strong demand in emerging African markets with growing middle class."
        competition, profit, market_size = "High", "High", "$380B global luxury market"
        summary = (f"The market for {idea} represents a significant opportunity, particularly in urban "
                   f"West African markets where demand for premium and luxury goods is growing rapidly "
                   f"among aspirational consumers. Authentication and trust are key differentiators.")
        recs = ["Partner with verified luxury goods authenticators to build trust",
                "Target affluent urban areas in Accra, Lagos and Nairobi first",
                "Offer layaway or instalment plans to broaden your customer base",
                "Build a strong Instagram and social media presence — luxury buyers research online",
                "Consider a consignment model to reduce inventory risk"]
        risks = ["High counterfeit risk damages brand reputation",
                 "Currency fluctuation affects import costs significantly",
                 "Limited customer base in early stages"]
    elif is_food:
        pricing = {"budget": "$5 - $15", "mid": "$15 - $40", "premium": "$40 - $100"}
        verdict_reason = "Food and beverage businesses have consistent demand with strong repeat customer potential."
        competition, profit, market_size = "High", "Medium", "$9T global food industry"
        summary = (f"The {idea} market benefits from consistent consumer demand and strong repeat purchase "
                   f"behaviour. Success depends on quality, location and building a loyal local customer base.")
        recs = ["Start with a small test location or market stall before scaling",
                "Develop a signature item that creates word-of-mouth marketing",
                "Use social media to showcase food preparation and quality",
                "Build a delivery partnership with Bolt Food or similar platforms",
                "Focus on food hygiene certification to build customer trust"]
        risks = ["High competition from established local eateries",
                 "Food spoilage and supply chain inconsistency",
                 "Location dependency for foot traffic"]
    elif is_tech:
        pricing = {"budget": "Free / Freemium", "mid": "$10 - $50/month", "premium": "$100 - $500/month"}
        verdict_reason = "Tech and software products have high scalability and low marginal costs once built."
        competition, profit, market_size = "Medium", "High", "$700B+ global software market"
        summary = (f"The {idea} space presents a high-growth opportunity with digital distribution and the "
                   f"ability to scale globally from day one. Finding an underserved niche is key to traction.")
        recs = ["Validate the core feature with 10 real users before building",
                "Choose a freemium model to lower the barrier for early adoption",
                "Focus on one specific user persona and problem to start",
                "Build in public — share your progress to attract early users",
                "Prioritise mobile-first design for the African market"]
        risks = ["High competition from international tech giants",
                 "Long development timelines before revenue",
                 "Customer acquisition costs can be high in early stages"]
    elif is_fashion:
        pricing = {"budget": "$20 - $80", "mid": "$80 - $300", "premium": "$300 - $1,000"}
        verdict_reason = "Fashion and apparel show strong consumer demand especially in urban African markets."
        competition, profit, market_size = "High", "Medium", "$2.5T global fashion market"
        summary = (f"The {idea} market is large and growing, with social media driving rapid trend cycles. "
                   f"Differentiation through unique design or a strong brand story is essential.")
        recs = ["Build a strong visual brand identity on Instagram and TikTok",
                "Start with a small capsule collection to test demand",
                "Partner with local influencers for authentic reach",
                "Offer made-to-order to reduce inventory risk",
                "Consider Afrocentric designs — a growing global trend"]
        risks = ["Fast-changing fashion trends require constant new inventory",
                 "High competition from fast fashion imports",
                 "Returns and sizing issues in online sales"]
    else:
        pricing = {"budget": "$20 - $60", "mid": "$60 - $200", "premium": "$200 - $500"}
        verdict_reason = "Initial market signals suggest viable demand for this idea with the right positioning."
        competition, profit, market_size = "Medium", "Medium", "Multi-billion dollar addressable market"
        summary = (f"The {idea} market shows promising potential with a clear customer need and room for "
                   f"differentiated positioning. Success depends on execution and customer acquisition.")
        recs = ["Start by validating demand with a small pilot before full launch",
                "Identify and deeply understand your top 3 competitors",
                "Focus on one specific customer segment rather than targeting everyone",
                "Build an online presence early — social media and a simple website",
                "Track your unit economics closely from day one"]
        risks = ["Market competition may be stronger than anticipated",
                 "Customer acquisition costs in early stages",
                 "Cash flow management during growth phase"]

    return {
        "summary": summary,
        "target_market": "Entrepreneurs, consumers and businesses in urban African markets",
        "verdict": "GO",
        "verdict_reason": verdict_reason,
        "recommendations": recs,
        "key_risks": risks,
        "pricing": pricing,
        "competition_level": competition,
        "profit_potential": profit,
        "market_size": market_size,
    }