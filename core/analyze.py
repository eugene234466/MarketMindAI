# ============================================================
# CORE/ANALYZE.PY — Analysis Pipeline
# ============================================================

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


def _import_modules():
    global analyze_idea, get_market_data, get_competitors
    global get_ecommerce_data, predict_sales, identify_niches

    from core.groq_client         import analyze_idea      # ← changed
    from core.market_researcher   import get_market_data
    from core.competitor_analyzer import get_competitors
    from core.ecommerce_scraper   import get_ecommerce_data
    from core.sales_predictor     import predict_sales
    from core.niche_identifier    import identify_niches

analyze_idea       = None
get_market_data    = None
get_competitors    = None
get_ecommerce_data = None
predict_sales      = None
identify_niches    = None


def _fallback_ai(idea: str) -> dict:
    return {
        "summary"          : "Analysis unavailable — please retry.",
        "verdict"          : "GO",
        "verdict_reason"   : "Could not complete analysis. Please retry.",
        "recommendations"  : ["Validate with a small test market", "Survey 10-20 potential customers"],
        "key_risks"        : ["Analysis incomplete — manually review competition"],
        "pricing"          : {"budget": "N/A", "mid": "N/A", "premium": "N/A"},
        "competition_level": "Medium",
        "profit_potential" : "Medium",
        "market_size"      : "N/A",
        "target_market"    : "General consumers",
    }

def _fallback_market() -> dict:
    return {
        "market_size"      : "N/A",
        "competition_level": "Medium",
        "profit_potential" : "Medium",
        "trend_score"      : 5,
        "trends"           : {"dates": [], "values": []},
        "trends_summary"   : "Trend data unavailable.",
    }

def _fallback_forecast() -> dict:
    return {
        "months": [], "revenue": [], "trend": [],
        "total_year": 0, "peak_month": "N/A",
        "growth_rate": "N/A", "summary": "",
    }


def run_pipeline(idea: str) -> dict:
    _import_modules()
    pipeline: dict = {}

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(analyze_idea,       idea): "ai_insights",
                executor.submit(get_market_data,    idea): "market_data",
                executor.submit(get_competitors,    idea): "competitors",
                executor.submit(get_ecommerce_data, idea): "ecommerce",
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    pipeline[key] = future.result()
                    print(f"[Pipeline] ✓ {key}")
                except Exception as e:
                    print(f"[Pipeline] ✗ {key}: {e}")
                    pipeline[key] = None
    except Exception as e:
        print(f"[Pipeline] Executor error: {e}")

    market_data = pipeline.get("market_data") or _fallback_market()

    try:
        pipeline["sales_forecast"] = predict_sales(market_data)
    except Exception as e:
        print(f"[Pipeline] ✗ sales_forecast: {e}")
        pipeline["sales_forecast"] = None

    try:
        pipeline["niches"] = identify_niches(idea, market_data)
    except Exception as e:
        print(f"[Pipeline] ✗ niches: {e}")
        pipeline["niches"] = None

    return {
        "idea"          : idea,
        "ai_insights"   : pipeline.get("ai_insights")    or _fallback_ai(idea),
        "market_data"   : market_data,
        "competitors"   : pipeline.get("competitors")    or [],
        "ecommerce"     : pipeline.get("ecommerce")      or {},
        "sales_forecast": pipeline.get("sales_forecast") or _fallback_forecast(),
        "niches"        : pipeline.get("niches")         or [],
        "created_at"    : datetime.now().strftime("%B %d, %Y %H:%M"),
        "from_cache"    : False,
    }
