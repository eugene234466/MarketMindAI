# ============================================================
# CORE/MARKET_RESEARCHER.PY — Market Research
# Uses pytrends (Google Trends) — completely free
# No SerpAPI calls at all
# ============================================================

import time
import hashlib
from pytrends.request import TrendReq
from core.gemini_client import call_gemini
import json

# ── IN-MEMORY CACHE ──────────────────────────────────────────
_market_cache = {}

def _cache_key(idea):
    return hashlib.md5(idea.strip().lower().encode()).hexdigest()


# ── MAIN FUNCTION ────────────────────────────────────────────
def get_market_data(idea):
    print(f"Researching market for: {idea}")

    # ── CHECK CACHE ──────────────────────────────────────────
    key = _cache_key(idea)
    if key in _market_cache:
        print("Market cache hit")
        return _market_cache[key]

    # ── GET TREND DATA ───────────────────────────────────────
    trends_data = get_trends(idea)

    # ── GET AI MARKET SUMMARY ────────────────────────────────
    ai_summary  = get_ai_market_summary(idea, trends_data)

    # ── BUILD RESULT ─────────────────────────────────────────
    trend_score = calculate_trend_score(trends_data)

    result = {
        "market_size"      : ai_summary.get("market_size",       "N/A"),
        "competition_level": ai_summary.get("competition_level", "Medium"),
        "profit_potential" : ai_summary.get("profit_potential",  "Medium"),
        "trend_score"      : trend_score,
        "trends_summary"   : ai_summary.get("summary",           ""),
        "trends"           : trends_data,
        "keywords"         : ai_summary.get("keywords",          [idea])
    }

    # ── STORE IN CACHE ────────────────────────────────────────
    if len(_market_cache) >= 50:
        del _market_cache[next(iter(_market_cache))]
    _market_cache[key] = result

    print("Market research complete")
    return result


# ── GOOGLE TRENDS (FREE) ─────────────────────────────────────
def get_trends(idea):
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

        # ── CLEAN KEYWORD ─────────────────────────────────────
        keyword = idea[:100]
        keywords = extract_keywords(keyword)

        pytrends.build_payload(
            kw_list   = [keywords[0]],
            cat       = 0,
            timeframe = "today 12-m",
            geo       = "",
            gprop     = ""
        )

        df = pytrends.interest_over_time()

        if df is not None and not df.empty:
            col    = df.columns[0]
            dates  = df.index.strftime("%Y-%m-%d").tolist()
            values = df[col].tolist()

            return {
                "dates"  : dates,
                "values" : values
            }

    except Exception as e:
        print(f"Trends error: {e}")

    return {"dates": [], "values": []}


# ── EXTRACT SHORT KEYWORDS ───────────────────────────────────
def extract_keywords(idea):
    # Remove common words, keep core keywords
    stopwords = [
        "for", "the", "and", "with", "in", "on",
        "at", "to", "a", "an", "of", "my", "your"
    ]
    words    = idea.lower().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    # Return top 2 keywords max (pytrends limit)
    return keywords[:2] if keywords else [idea.split()[0]]


# ── CALCULATE TREND SCORE ────────────────────────────────────
def calculate_trend_score(trends_data):
    values = trends_data.get("values", [])

    if not values:
        return 5

    # Use average of last 3 months
    recent  = values[-12:] if len(values) >= 12 else values
    avg     = sum(recent) / len(recent)

    # Scale 0-100 → 0-10
    score   = round((avg / 100) * 10, 1)
    return max(1, min(10, score))


# ── AI MARKET SUMMARY (GEMINI — 1 CALL ONLY) ─────────────────
def get_ai_market_summary(idea, trends_data):
    trend_direction = "growing"
    values = trends_data.get("values", [])

    if len(values) >= 6:
        if values[-1] > values[-6]:
            trend_direction = "growing"
        elif values[-1] < values[-6]:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

    prompt = f"""
    Provide a brief market overview for: "{idea}"
    Google Trends shows this market is currently {trend_direction}.

    Respond ONLY with valid JSON, no markdown:
    {{
        "market_size"      : "$XB global market",
        "competition_level": "Low" or "Medium" or "High",
        "profit_potential" : "Low" or "Medium" or "High",
        "summary"          : "2 sentence market overview",
        "keywords"         : ["keyword1", "keyword2"]
    }}
    """

    result = call_gemini(prompt)

    if result:
        try:
            clean = result.strip()
            if "```" in clean:
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip())
        except Exception as e:
            print(f"Market AI parse error: {e}")

    return {
        "market_size"      : "N/A",
        "competition_level": "Medium",
        "profit_potential" : "Medium",
        "summary"          : f"Market data for {idea}",
        "keywords"         : [idea.split()[0]]
    }
