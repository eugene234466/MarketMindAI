# ============================================================
# CORE/COMPETITOR_ANALYZER.PY — Competitor analysis
# URL discovery: SearchProvider registry (Zenserp) with the old
# googlesearch code as a fallback. Then scrape + AI gap fill.
# NOTE: market_share / strength / weakness values are still
# placeholders here. Milestone 4 replaces them with evidence.
# ============================================================

import time
import hashlib

import requests
from bs4 import BeautifulSoup

from core.groq_client import call_groq, _parse_json
from core.providers.registry import registry
from core.providers.base import SearchProvider
from database.db import save_evidence

try:
    from googlesearch import search as google_search
    GSEARCH_AVAILABLE = True
except ImportError:
    GSEARCH_AVAILABLE = False

_competitor_cache = {}


def _cache_key(idea):
    return hashlib.md5(idea.strip().lower().encode()).hexdigest()


LOCATION_WORDS = [
    "in ghana", "in nigeria", "in africa", "in west africa",
    "in east africa", "in south africa", "in north africa",
    "in accra", "in lagos", "in nairobi", "in kenya",
    "in abuja", "in kumasi", "in cape town", "in johannesburg",
    "in egypt", "in senegal", "in ivory coast",
    "in the us", "in the uk", "in usa", "in united states",
    "in united kingdom", "in canada", "in australia",
    "in europe", "in asia", "in india", "in china",
    "online", "near me", "locally",
]

SKIP_DOMAINS = [
    "wikipedia.org", "reddit.com", "quora.com",
    "youtube.com", "facebook.com", "instagram.com",
    "twitter.com", "tiktok.com", "pinterest.com",
    "linkedin.com", "medium.com", "forbes.com",
    "businessinsider.com", "techcrunch.com",
    "news.", ".gov", ".edu",
]


# ── MAIN FUNCTION ────────────────────────────────────────────
def get_competitors(idea):
    print(f'Analyzing competitors for: "{idea}"')

    key = _cache_key(idea)
    if key in _competitor_cache:
        print("Competitor cache hit")
        return _competitor_cache[key]

    clean_idea = clean_query(idea)
    print(f"Cleaned query: '{clean_idea}'")

    queries     = build_queries(clean_idea, idea)
    urls        = find_competitor_urls(queries)
    competitors = enrich_competitors(urls, clean_idea) if urls else []

    if len(competitors) < 3:
        print(f"Only {len(competitors)} scraped — using Groq to fill gaps")
        ai_competitors = get_ai_competitors(idea)

        existing_names = {c["name"].lower() for c in competitors}
        for ac in ai_competitors:
            if not isinstance(ac, dict) or not ac.get("name"):
                continue
            if ac["name"].lower() not in existing_names:
                competitors.append(ac)
            if len(competitors) >= 5:
                break

    if len(_competitor_cache) >= 50:
        del _competitor_cache[next(iter(_competitor_cache))]
    _competitor_cache[key] = competitors[:6]

    print(f"Found {len(competitors)} competitors")
    return competitors[:6]


# ── QUERY HELPERS ────────────────────────────────────────────
def clean_query(idea):
    clean = idea.lower().strip()
    for loc in LOCATION_WORDS:
        clean = clean.replace(loc, "")
    clean = " ".join(clean.split()).strip()
    return clean.title() if clean else idea


def build_queries(clean_idea, original_idea):
    queries = [
        f"{clean_idea} competitors",
        f"{clean_idea} brand official website",
        f"best {clean_idea} companies",
        f"{clean_idea} buy online store",
        f"top {clean_idea} brands",
    ]
    idea_lower = clean_idea.lower()

    if any(w in idea_lower for w in ["app", "software", "saas", "platform", "tool"]):
        queries[:0] = [f"{clean_idea} alternatives", f"{clean_idea} vs competitors"]
    if any(w in idea_lower for w in ["bag", "shoe", "fashion", "clothing", "wear", "luxury"]):
        queries[:0] = [f"{clean_idea} brand shop", f"buy {clean_idea} online"]
    if any(w in idea_lower for w in ["food", "restaurant", "cafe", "delivery", "catering"]):
        queries[:0] = [f"{clean_idea} chain restaurant", f"popular {clean_idea} franchise"]
    if any(w in idea_lower for w in ["service", "agency", "consulting", "freelance"]):
        queries[:0] = [f"{clean_idea} agency", f"top {clean_idea} service providers"]

    return queries[:5]


# ── URL DISCOVERY ────────────────────────────────────────────
def find_competitor_urls(queries):
    """Use registered SearchProviders. Fall back to googlesearch when none
    is configured, or when every provider returned nothing (quota/outage)."""
    providers = registry.get_all(SearchProvider)
    if not providers:
        return _find_urls_googlesearch(queries)

    seen, urls, collected = set(), [], []

    for query in queries[:3]:
        for provider in providers:
            try:
                results = provider.search(query, limit=5)
            except Exception as e:
                print(f"Search provider '{provider.name}' failed: {type(e).__name__}")
                continue

            for r in results:
                if any(skip in r.url for skip in SKIP_DOMAINS):
                    continue
                parts  = r.url.split("/")
                domain = parts[2] if len(parts) > 2 else r.url
                if domain in seen:
                    continue
                seen.add(domain)
                urls.append(r.url)
                collected.append(r)

    if collected:
        # analysis_id is wired to the real research id in Milestone 4
        save_evidence(collected, analysis_id=None)

    if not urls:
        return _find_urls_googlesearch(queries)

    return urls[:8]


def _find_urls_googlesearch(queries):
    """Original free fallback."""
    if not GSEARCH_AVAILABLE:
        return []

    seen, urls = set(), []

    for query in queries[:3]:
        try:
            results = list(google_search(query, num_results=5, sleep_interval=2))

            for url in results:
                if any(skip in url for skip in SKIP_DOMAINS):
                    continue
                domain = url.split("/")[2] if len(url.split("/")) > 2 else url
                if domain not in seen:
                    seen.add(domain)
                    urls.append(url)

            time.sleep(2)

        except Exception as e:
            print(f"Search error for '{query}': {e}")
            continue

    return urls[:8]


# ── SCRAPE + ENRICH ──────────────────────────────────────────
def enrich_competitors(urls, idea):
    competitors = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept"    : "text/html,application/xhtml+xml,*/*;q=0.8",
    }

    shares     = [30, 22, 16, 12, 9, 6]
    strengths  = [
        "Strong global brand recognition",
        "Large customer base and loyalty",
        "Competitive pricing strategy",
        "Wide product range",
        "Strong digital presence",
    ]
    weaknesses = [
        "Premium pricing limits reach",
        "Limited local market focus",
        "Slow to adapt to trends",
        "Inconsistent customer service",
        "Limited distribution channels",
    ]

    for i, url in enumerate(urls[:5]):
        try:
            resp = requests.get(url, headers=headers, timeout=4)
            soup = BeautifulSoup(resp.text, "html.parser")

            name     = extract_name(soup, url)
            desc     = extract_description(soup)
            has_shop = detect_shop(soup, url)

            share  = shares[i] if i < len(shares) else 3
            threat = "High" if share >= 20 else "Medium" if share >= 10 else "Low"

            competitors.append({
                "name"        : name,
                "url"         : url,
                "market_share": f"{share}%",
                "threat"      : threat,
                "strength"    : desc[:70] if desc else strengths[i % len(strengths)],
                "weakness"    : weaknesses[i % len(weaknesses)],
                "has_shop"    : has_shop,
            })

            time.sleep(0.8)

        except Exception as e:
            print(f"Scrape failed for {url}: {e}")
            continue

    return competitors


def extract_name(soup, url):
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content"):
        return og["content"].strip()[:40]

    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        for sep in ["|", "-", "–", ":", "•"]:
            if sep in title:
                title = title.split(sep)[0].strip()
        return title[:40]

    domain = url.split("/")[2].replace("www.", "")
    return domain.split(".")[0].title()


def extract_description(soup):
    for attr in [{"name": "description"}, {"property": "og:description"}]:
        tag = soup.find("meta", attrs=attr)
        if tag and tag.get("content"):
            return tag["content"].strip()[:120]
    return ""


def detect_shop(soup, url):
    signals = ["add to cart", "buy now", "shop now", "shopify",
               "woocommerce", "checkout", "add to bag"]
    text = soup.get_text().lower()
    return any(s in text for s in signals)


# ── AI FALLBACK ──────────────────────────────────────────────
def get_ai_competitors(idea):
    print("Filling competitor gaps with Groq")

    prompt = f"""
    List 5 real, well-known competitors for this business idea: "{idea}"
    Include global and regional players if relevant.

    Respond ONLY with a valid JSON array, no markdown, no backticks:
    [
        {{
            "name"        : "Company Name",
            "url"         : "https://example.com",
            "market_share": "25%",
            "threat"      : "High",
            "strength"    : "Strong global brand and distribution",
            "weakness"    : "Premium pricing limits accessibility"
        }}
    ]

    threat must be one of: High, Medium, Low
    """

    parsed = _parse_json(call_groq(prompt))

    if isinstance(parsed, list):
        return parsed[:5]

    return []