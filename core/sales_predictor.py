# ============================================================
# CORE/SALES_PREDICTOR.PY — ML Sales Forecasting
# Uses scikit-learn only (no Prophet — too heavy for Railway)
# Polynomial regression + seasonal overlay for realistic curves
# ============================================================

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
    import math
    result = []
    for i, v in enumerate(values):
        seasonal = 1 + 0.08 * math.sin((i / 12) * 2 * math.pi - math.pi / 2)
        result.append(v * seasonal)
    return result


# ── 6. CONVERT TREND SCORES → REVENUE ───────────────────────

def convert_to_revenue(forecast: list, market_data: dict) -> list:
    try:
        market_size = market_data.get("market_size", "N/A")
        competition = market_data.get("competition_level", "Medium")

        size_multipliers = {
            "$10B+"        : 50000,
            "$1B - $10B"   : 20000,
            "$100M - $1B"  : 10000,
            "$10M - $100M" : 5000,
            "$1M - $10M"   : 1000,
            "N/A"          : 2000,
        }
        competition_factors = {
            "High"  : 0.05,
            "Medium": 0.10,
            "Low"   : 0.20,
        }

        base       = size_multipliers.get(market_size, 2000)
        factor     = competition_factors.get(competition, 0.10)
        multiplier = base * factor

        return [max(0, round(score * multiplier)) for score in forecast]

    except Exception as e:
        print(f"[convert_to_revenue] {e}")
        return [round(5000 * (1 + 0.08 * i)) for i in range(12)]


# ── 7. MONTH LABELS ──────────────────────────────────────────

def generate_month_labels() -> list:
    now = datetime.now()
    return [(now + timedelta(days=30 * i)).strftime("%b %Y") for i in range(1, 13)]


# ── 8. TREND LINE ────────────────────────────────────────────

def calculate_trend_line(revenue: list) -> list:
    try:
        X = np.array(range(len(revenue))).reshape(-1, 1)
        y = np.array(revenue, dtype=float)
        model = LinearRegression()
        model.fit(X, y)
        return [round(t) for t in model.predict(X).tolist()]
    except:
        return revenue


# ── 9. PEAK MONTH ────────────────────────────────────────────

def get_peak_month(revenue: list, months: list) -> str:
    try:
        return months[revenue.index(max(revenue))]
    except:
        return "N/A"


# ── 10. GROWTH RATE ──────────────────────────────────────────

def calculate_growth_rate(revenue: list) -> str:
    try:
        if not revenue or revenue[0] == 0:
            return "N/A"
        growth = ((revenue[-1] - revenue[0]) / revenue[0]) * 100
        return f"+{round(growth)}%" if growth >= 0 else f"{round(growth)}%"
    except:
        return "N/A"


# ── 11. SUMMARY ──────────────────────────────────────────────

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
    except:
        return "Sales forecast data unavailable."


# ── 12. FALLBACK ─────────────────────────────────────────────

def get_fallback_forecast() -> dict:
    months  = generate_month_labels()
    revenue = [round(5000 * (1 + 0.08 * i)) for i in range(12)]
    return {
        "months"     : months,
        "revenue"    : revenue,
        "trend"      : revenue,
        "total_year" : sum(revenue),
        "peak_month" : months[-1],
        "growth_rate": "+88%",
        "summary"    : "Forecast based on estimated market data.",
    }
