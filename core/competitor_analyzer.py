# ============================================================
# CORE/COMPETITOR_ANALYZER.PY
# ============================================================

import time
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from core.groq_client import call_groq

try:
    from googlesearch import search as google_search
    GSEARCH_AVAILABLE = True
except ImportError:
    GSEARCH_AVAILABLE = False

_competitor_cache = {}

def _cache_key(idea):
    return hashlib.md5(idea.strip().lower().encode()).hexdigest()

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
    except Exception:
        return None

LOCATION_WORDS = [
    "in ghana","in nigeria","in africa","in west africa","in east africa",
    "in south africa","in north africa","in accra","in lagos","in nairobi",
    "in kenya","in abuja","in kumasi","in cape town","in johannesburg",
    "in egypt","in senegal","in ivory coast","in the us","in the uk",
    "in usa","in united states","in united kingdom","in canada","in australia",
    "in europe","in asia","in india","in china","online","near me","locally",
]

SKIP_DOMAINS = [
    "wikipedia.org","reddit.com","quora.com","youtube.com","facebook.com",
    "instagram.com","twitter.com","tiktok.com","pinterest.com","linkedin.com",
    "medium.com","forbes.com","businessinsider.com","techcrunch.com","news.",".gov",".edu",
]

def get_competitors(idea):
    print(f'Analyzing competitors for: "{idea}"')
    key = _cache_key(idea)
    if key in _competitor_cache:
        print("Competitor cache hit")
        return _competitor_cache[key]

    clean_idea  = clean_query(idea)
    print(f"Cleaned query: '{clean_idea}'")
    queries     = build_queries(clean_idea, idea)
    urls        = find_competitor_urls(queries)
    competitors = enrich_competitors(urls, clean_idea) if urls else []

    if len(competitors) < 3:
        print(f"Only {len(competitors)} scraped — using Groq to fill gaps")
        ai_competitors  = get_ai_competitors(idea)
        existing_names  = {c["name"].lower() for c in competitors}
        for ac in ai_competitors:
            if ac["name"].lower() not in existing_names:
                competitors.append(ac)
            if len(competitors) >= 5:
                break

    if len(_competitor_cache) >= 50:
        del _competitor_cache[next(iter(_competitor_cache))]
    _competitor_cache[key] = competitors[:6]
    print(f"Found {len(competitors)} competitors")
    return competitors[:6]

def clean_query(idea):
    clean = idea.lower().strip()
    for loc in LOCATION_WORDS:
        clean = clean.replace(loc, "")
    return " ".join(clean.split()).strip().title() or idea

def build_queries(clean_idea, original_idea):
    queries = [
        f"{clean_idea} competitors",
        f"{clean_idea} brand official website",
        f"best {clean_idea} companies",
        f"{clean_idea} buy online store",
        f"top {clean_idea} brands",
    ]
    idea_lower = clean_idea.lower()
    if any(w in idea_lower for w in ["app","software","saas","platform","tool"]):
        queries[:0] = [f"{clean_idea} alternatives", f"{clean_idea} vs competitors"]
    if any(w in idea_lower for w in ["bag","shoe","fashion","clothing","wear","luxury"]):
        queries[:0] = [f"{clean_idea} brand shop", f"buy {clean_idea} online"]
    if any(w in idea_lower for w in ["food","restaurant","cafe","delivery","catering"]):
        queries[:0] = [f"{clean_idea} chain restaurant", f"popular {clean_idea} franchise"]
    if any(w in idea_lower for w in ["service","agency","consulting","freelance"]):
        queries[:0] = [f"{clean_idea} agency", f"top {clean_idea} service providers"]
    return queries[:5]

def find_competitor_urls(queries):
    if not GSEARCH_AVAILABLE:
        return []
    seen, urls = set(), []
    for query in queries[:3]:
        try:
            for url in list(google_search(query, num_results=5, sleep_interval=2)):
                if any(skip in url for skip in SKIP_DOMAINS):
                    continue
                domain = url.split("/")[2] if len(url.split("/")) > 2 else url
                if domain not in seen:
                    seen.add(domain)
                    urls.append(url)
            time.sleep(2)
        except Exception as e:
            print(f"Search error for '{query}': {e}")
    return urls[:8]

def enrich_competitors(urls, idea):
    competitors = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
    shares  = [30, 22, 16, 12, 9, 6]
    strengths  = ["Strong global brand recognition","Large customer base and loyalty","Competitive pricing strategy","Wide product range","Strong digital presence"]
    weaknesses = ["Premium pricing limits reach","Limited local market focus","Slow to adapt to trends","Inconsistent customer service","Limited distribution channels"]

    for i, url in enumerate(urls[:5]):
        try:
            resp = requests.get(url, headers=headers, timeout=4)
            soup = BeautifulSoup(resp.text, "html.parser")
            name  = extract_name(soup, url)
            desc  = extract_description(soup)
            share = shares[i] if i < len(shares) else 3
            competitors.append({
                "name": name, "url": url, "market_share": f"{share}%",
                "threat": "High" if share >= 20 else "Medium" if share >= 10 else "Low",
                "strength": desc[:70] if desc else strengths[i % len(strengths)],
                "weakness": weaknesses[i % len(weaknesses)],
                "has_shop": detect_shop(soup, url)
            })
            time.sleep(0.8)
        except Exception as e:
            print(f"Scrape failed for {url}: {e}")
    return competitors

def extract_name(soup, url):
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content"):
        return og["content"].strip()[:40]
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        for sep in ["|","-","–",":","•"]:
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
    signals = ["add to cart","buy now","shop now","shopify","woocommerce","checkout","add to bag"]
    return any(s in soup.get_text().lower() for s in signals)

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
    result = call_groq(prompt)
    parsed = _parse_json(result)
    return parsed[:5] if isinstance(parsed, list) else []
