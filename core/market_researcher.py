# ============================================================
# CORE/MARKET_RESEARCHER.PY
# ============================================================

import time
import json
import hashlib
from pytrends.request import TrendReq
from core.groq_client import call_groq

_market_cache = {}

def _cache_key(idea):
    return hashlib.md5(idea.strip().lower().encode()).hexdigest()

def get_market_data(idea):
    print(f"Researching market for: {idea}")
    key = _cache_key(idea)
    if key in _market_cache:
        print("Market cache hit")
        return _market_cache[key]

    trends_data = get_trends(idea)
    ai_summary  = get_ai_market_summary(idea, trends_data)
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

    if len(_market_cache) >= 50:
        del _market_cache[next(iter(_market_cache))]
    _market_cache[key] = result

    print("Market research complete")
    return result

def get_trends(idea):
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        keywords = extract_keywords(idea[:100])
        pytrends.build_payload(kw_list=[keywords[0]], cat=0, timeframe="today 12-m", geo="", gprop="")
        df = pytrends.interest_over_time()
        if df is not None and not df.empty:
            col = df.columns[0]
            return {"dates": df.index.strftime("%Y-%m-%d").tolist(), "values": df[col].tolist()}
    except Exception as e:
        print(f"Trends error: {e}")
    return {"dates": [], "values": []}

def extract_keywords(idea):
    stopwords = ["for","the","and","with","in","on","at","to","a","an","of","my","your"]
    words = idea.lower().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return keywords[:2] if keywords else [idea.split()[0]]

def calculate_trend_score(trends_data):
    values = trends_data.get("values", [])
    if not values:
        return 5
    recent = values[-12:] if len(values) >= 12 else values
    avg    = sum(recent) / len(recent)
    return max(1, min(10, round((avg / 100) * 10, 1)))

def get_ai_market_summary(idea, trends_data):
    values = trends_data.get("values", [])
    trend_direction = "stable"
    if len(values) >= 6:
        trend_direction = "growing" if values[-1] > values[-6] else "declining" if values[-1] < values[-6] else "stable"

    prompt = f"""
    Provide a brief market overview for: "{idea}"
    Google Trends shows this market is currently {trend_direction}.

    Respond ONLY with valid JSON, no markdown:
    {{
        "market_size"      : "$XB global market",
        "competition_level": "Low",
        "profit_potential" : "Medium",
        "summary"          : "2 sentence market overview",
        "keywords"         : ["keyword1", "keyword2"]
    }}

    competition_level must be one of: Low, Medium, High
    profit_potential must be one of: Low, Medium, High
    """

    result = call_groq(prompt)
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

    return {"market_size": "N/A", "competition_level": "Medium", "profit_potential": "Medium",
            "summary": f"Market data for {idea}", "keywords": [idea.split()[0]]}
