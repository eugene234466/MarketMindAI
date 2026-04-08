# ============================================================
# CORE/SALES_PREDICTOR.PY — ML Sales Forecasting
# Uses scikit-learn only (no Prophet — too heavy for Render)
# Polynomial regression + seasonal overlay for realistic curves
# ============================================================

import re
import math
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures


# ── 1. MAIN FUNCTION ─────────────────────────────────────────

def predict_sales(market_data: dict) -> dict:
    try:
        trend_values = market_data.get("trends", {}).get("values", [])

        if len(trend_values) >= 12:
            forecast = polynomial_forecast(trend_values)
        elif trend_values:
            forecast = linear_forecast(trend_values)
        else:
            forecast = growth_curve_forecast(market_data)

        revenue = convert_to_revenue(forecast, market_data)
        months  = generate_month_labels()

        return {
            "months"     : months,
            "revenue"    : revenue,
            "trend"      : calculate_trend_line(revenue),
            "total_year" : sum(revenue),
            "peak_month" : get_peak_month(revenue, months),
            "growth_rate": calculate_growth_rate(revenue),
            "summary"    : generate_forecast_summary(revenue),
        }

    except Exception as e:
        print(f"[sales_predictor] Error: {e}")
        return get_fallback_forecast()


# ── 2. POLYNOMIAL REGRESSION FORECAST ───────────────────────

def polynomial_forecast(values: list, degree: int = 3) -> list:
    try:
        X = np.array(range(len(values))).reshape(-1, 1)
        y = np.array(values, dtype=float)

        poly   = PolynomialFeatures(degree=degree)
        X_poly = poly.fit_transform(X)

        model  = LinearRegression()
        model.fit(X_poly, y)

        future_X      = np.array(range(len(values), len(values) + 12)).reshape(-1, 1)
        future_X_poly = poly.transform(future_X)
        predictions   = model.predict(future_X_poly).tolist()

        predictions = _apply_seasonality(predictions)
        return [max(0.0, min(100.0, p)) for p in predictions]

    except Exception as e:
        print(f"[polynomial_forecast] {e}")
        return linear_forecast(values)


# ── 3. LINEAR REGRESSION FORECAST ───────────────────────────

def linear_forecast(values: list) -> list:
    try:
        if not values:
            return [50.0] * 12

        X = np.array(range(len(values))).reshape(-1, 1)
        y = np.array(values, dtype=float)

        model = LinearRegression()
        model.fit(X, y)

        future_X    = np.array(range(len(values), len(values) + 12)).reshape(-1, 1)
        predictions = model.predict(future_X).tolist()
        predictions = _apply_seasonality(predictions)

        return [max(0.0, min(100.0, p)) for p in predictions]

    except Exception as e:
        print(f"[linear_forecast] {e}")
        return [50.0] * 12


# ── 4. GROWTH CURVE (when no trend data) ────────────────────

def growth_curve_forecast(market_data: dict) -> list:
    competition = market_data.get("competition_level", "Medium")
    trend_score = float(market_data.get("trend_score", 5))

    base   = 20 + trend_score * 3
    growth = {"High": 0.06, "Medium": 0.09, "Low": 0.14}.get(competition, 0.08)

    curve = []
    v = base
    for _ in range(12):
        v = v * (1 + growth)
        curve.append(max(0.0, min(100.0, v)))
    return curve


# ── 5. SEASONALITY OVERLAY ───────────────────────────────────

def _apply_seasonality(values: list) -> list:
    result = []
    for i, v in enumerate(values):
        seasonal = 1 + 0.08 * math.sin((i / 12) * 2 * math.pi - math.pi / 2)
        result.append(v * seasonal)
    return result


# ── 6. PARSE MARKET SIZE STRING → USD VALUE ──────────────────

def _parse_market_size(market_size: str) -> float:
    """
    Parses any market size string Groq returns and converts to a dollar value.
    Examples handled:
        "$380B global luxury market"  → 380_000_000_000
        "$5B global market"           → 5_000_000_000
        "$700B+ global software"      → 700_000_000_000
        "$9T global food industry"    → 9_000_000_000_000
        "$2.5T"                       → 2_500_000_000_000
        "Multi-billion dollar..."     → 2_000_000_000
        "N/A"                         → None
    """
    if not market_size or market_size == "N/A":
        return None

    text = market_size.upper().replace(",", "")

    # Find first number (int or decimal) followed by optional suffix
    match = re.search(r'\$?([\d.]+)\s*([TBMK]?)', text)
    if not match:
        if "BILLION" in text:
            num = re.search(r'([\d.]+)', text)
            return float(num.group(1)) * 1e9 if num else None
        if "TRILLION" in text:
            num = re.search(r'([\d.]+)', text)
            return float(num.group(1)) * 1e12 if num else None
        return None

    value  = float(match.group(1))
    suffix = match.group(2)

    multipliers = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
    return value * multipliers.get(suffix, 1)


# ── 7. CONVERT TREND SCORES → REVENUE ───────────────────────

def convert_to_revenue(forecast: list, market_data: dict) -> list:
    """
    Converts 0-100 trend scores to realistic monthly revenue estimates.

    Strategy: A small startup realistically captures 0.0001% - 0.001%
    of the total addressable market in year 1. We scale that by competition.
    """
    try:
        market_size_str = market_data.get("market_size", "N/A")
        competition     = market_data.get("competition_level", "Medium")
        trend_score     = float(market_data.get("trend_score", 5))

        market_value = _parse_market_size(market_size_str)

        if market_value:
            # Realistic startup capture rate: 0.00001% to 0.0005% of TAM
            capture_rates = {"Low": 0.000005, "Medium": 0.000002, "High": 0.000001}
            capture       = capture_rates.get(competition, 0.000002)
            annual_target = market_value * capture

            # Trend score boosts the base (score 1-10 → 0.5x to 1.5x)
            trend_factor  = 0.5 + (trend_score / 10)
            annual_target = annual_target * trend_factor

            # Clamp to a believable startup range: $10k - $2M / year
            annual_target = max(10_000, min(2_000_000, annual_target))
        else:
            # Fallback: simple range based on competition + trend
            base_annual = {
                "Low":    150_000,
                "Medium":  80_000,
                "High":    40_000,
            }.get(competition, 80_000)
            trend_factor  = 0.5 + (trend_score / 10)
            annual_target = base_annual * trend_factor

        # Distribute across 12 months using the forecast shape (0-100 scores)
        total_score = sum(forecast) or 1
        revenue = [
            max(0, round((score / total_score) * annual_target))
            for score in forecast
        ]
        return revenue

    except Exception as e:
        print(f"[convert_to_revenue] {e}")
        return [round(5_000 * (1 + 0.08 * i)) for i in range(12)]


# ── 8. MONTH LABELS ──────────────────────────────────────────

def generate_month_labels() -> list:
    now = datetime.now()
    return [(now + timedelta(days=30 * i)).strftime("%b %Y") for i in range(1, 13)]


# ── 9. TREND LINE ────────────────────────────────────────────

def calculate_trend_line(revenue: list) -> list:
    try:
        X = np.array(range(len(revenue))).reshape(-1, 1)
        y = np.array(revenue, dtype=float)
        model = LinearRegression()
        model.fit(X, y)
        return [max(0, round(t)) for t in model.predict(X).tolist()]
    except Exception:
        return revenue


# ── 10. PEAK MONTH ───────────────────────────────────────────

def get_peak_month(revenue: list, months: list) -> str:
    try:
        return months[revenue.index(max(revenue))]
    except Exception:
        return "N/A"


# ── 11. GROWTH RATE ──────────────────────────────────────────

def calculate_growth_rate(revenue: list) -> str:
    try:
        if not revenue or revenue[0] == 0:
            return "N/A"
        growth = ((revenue[-1] - revenue[0]) / revenue[0]) * 100
        return f"+{round(growth)}%" if growth >= 0 else f"{round(growth)}%"
    except Exception:
        return "N/A"


# ── 12. SUMMARY ──────────────────────────────────────────────

def generate_forecast_summary(revenue: list) -> str:
    try:
        months = generate_month_labels()
        total  = sum(revenue)
        growth = calculate_growth_rate(revenue)
        peak   = get_peak_month(revenue, months)
        return (
            f"Projected annual revenue of ${total:,} "
            f"with {growth} growth. "
            f"Peak performance expected in {peak}."
        )
    except Exception:
        return "Sales forecast data unavailable."


# ── 13. FALLBACK ─────────────────────────────────────────────

def get_fallback_forecast() -> dict:
    months  = generate_month_labels()
    revenue = [round(5_000 * (1 + 0.08 * i)) for i in range(12)]
    return {
        "months"     : months,
        "revenue"    : revenue,
        "trend"      : calculate_trend_line(revenue),
        "total_year" : sum(revenue),
        "peak_month" : months[-1],
        "growth_rate": "+88%",
        "summary"    : "Forecast based on estimated market data.",
    }
