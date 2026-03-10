# ============================================================
# CORE/ECOMMERCE_SCRAPER.PY — Ecommerce Data
# Parallel scraping — Amazon + Jumia + Tonaton
# Fast timeouts + in-memory caching
# ============================================================

import hashlib
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# ── IN-MEMORY CACHE ──────────────────────────────────────────
_ecom_cache = {}

def _cache_key(idea):
    return hashlib.md5(idea.strip().lower().encode()).hexdigest()

# ── BROWSER HEADERS ──────────────────────────────────────────
HEADERS = {
    "User-Agent"     : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept"         : "text/html,application/xhtml+xml,*/*;q=0.8",
}


# ── MAIN FUNCTION ────────────────────────────────────────────
def get_ecommerce_data(idea):
    print(f"Scraping ecommerce data for: {idea}")

    # ── CHECK CACHE ──────────────────────────────────────────
    key = _cache_key(idea)
    if key in _ecom_cache:
        print("Ecommerce cache hit")
        return _ecom_cache[key]

    # ── SCRAPE ALL 3 IN PARALLEL ─────────────────────────────
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            f_amazon  = executor.submit(scrape_amazon,  idea)
            f_jumia   = executor.submit(scrape_jumia,   idea)
            f_tonaton = executor.submit(scrape_tonaton, idea)

            result = {
                "amazon" : f_amazon.result(),
                "jumia"  : f_jumia.result(),
                "tonaton": f_tonaton.result(),
            }

    except Exception as e:
        print(f"Ecommerce parallel error: {e}")
        result = {"amazon": [], "jumia": [], "tonaton": []}

    result["summary"] = build_summary(result)

    # ── STORE IN CACHE ────────────────────────────────────────
    if len(_ecom_cache) >= 50:
        del _ecom_cache[next(iter(_ecom_cache))]
    _ecom_cache[key] = result

    print("Ecommerce data fetched")
    return result


# ── AMAZON SCRAPER ───────────────────────────────────────────
def scrape_amazon(idea):
    try:
        keyword = "+".join(idea.split()[:4])
        url     = f"https://www.amazon.com/s?k={keyword}"

        resp = requests.get(url, headers=HEADERS, timeout=4)
        soup = BeautifulSoup(resp.text, "html.parser")

        products = []
        items    = soup.select('[data-component-type="s-search-result"]')[:4]

        for item in items:
            try:
                title_el  = item.select_one("h2 a span")
                title     = title_el.text.strip()[:80] if title_el else None
                if not title:
                    continue

                price_el  = item.select_one(".a-price .a-offscreen")
                price     = price_el.text.strip() if price_el else "N/A"

                rating_el = item.select_one(".a-icon-alt")
                rating    = rating_el.text[:3] if rating_el else "N/A"

                reviews_el = item.select_one(".a-size-base.s-underline-text")
                reviews    = reviews_el.text.strip() if reviews_el else "0"

                products.append({
                    "title"  : title,
                    "price"  : price,
                    "rating" : rating,
                    "reviews": reviews,
                    "source" : "Amazon"
                })
            except Exception:
                continue

        return products

    except Exception as e:
        print(f"Amazon error: {e}")
        return []


# ── JUMIA SCRAPER ────────────────────────────────────────────
def scrape_jumia(idea):
    try:
        keyword = "-".join(idea.lower().split()[:4])
        url     = f"https://www.jumia.com.gh/catalog/?q={keyword}"

        resp = requests.get(url, headers=HEADERS, timeout=4)
        soup = BeautifulSoup(resp.text, "html.parser")

        products = []
        items    = soup.select("article.prd")[:4]

        for item in items:
            try:
                title_el = item.select_one(".name")
                title    = title_el.text.strip()[:80] if title_el else None
                if not title:
                    continue

                price_el = item.select_one(".prc")
                price    = price_el.text.strip() if price_el else "N/A"

                rating_el = item.select_one(".stars._s")
                rating    = rating_el.text.strip() if rating_el else "N/A"

                products.append({
                    "title"  : title,
                    "price"  : price,
                    "rating" : rating,
                    "reviews": "N/A",
                    "source" : "Jumia Ghana"
                })
            except Exception:
                continue

        return products

    except Exception as e:
        print(f"Jumia error: {e}")
        return []


# ── TONATON SCRAPER ──────────────────────────────────────────
def scrape_tonaton(idea):
    try:
        keyword = "+".join(idea.split()[:3])
        url     = f"https://www.tonaton.com/en/search?query={keyword}"

        resp = requests.get(url, headers=HEADERS, timeout=4)
        soup = BeautifulSoup(resp.text, "html.parser")

        products = []
        items    = soup.select(".product-card, .listing-card, .item-card")[:4]

        for item in items:
            try:
                title_el = item.select_one("h2, h3, .title, .name")
                title    = title_el.text.strip()[:80] if title_el else None
                if not title:
                    continue

                price_el = item.select_one(".price, .amount")
                price    = price_el.text.strip() if price_el else "N/A"

                products.append({
                    "title"  : title,
                    "price"  : price,
                    "rating" : "N/A",
                    "reviews": "N/A",
                    "source" : "Tonaton"
                })
            except Exception:
                continue

        return products

    except Exception as e:
        print(f"Tonaton error: {e}")
        return []


# ── PRICE SUMMARY ────────────────────────────────────────────
def build_summary(data):
    all_products = (
        data.get("amazon",  []) +
        data.get("jumia",   []) +
        data.get("tonaton", [])
    )

    prices = []
    for p in all_products:
        try:
            cleaned = (
                p.get("price", "")
                 .replace("$",  "")
                 .replace("GH₵","")
                 .replace("GHS","")
                 .replace(",",  "")
                 .strip()
            )
            price = float(cleaned.split()[0])
            prices.append(price)
        except Exception:
            continue

    if prices:
        return {
            "min_price"     : f"${min(prices):.2f}",
            "max_price"     : f"${max(prices):.2f}",
            "avg_price"     : f"${sum(prices)/len(prices):.2f}",
            "total_listings": len(all_products)
        }

    return {
        "min_price"     : "N/A",
        "max_price"     : "N/A",
        "avg_price"     : "N/A",
        "total_listings": len(all_products)
    }
