# ============================================================
# APP/ROUTES.PY — All URL Routes
# Google Auth removed | Terms route added
# ============================================================

import os
import json
import time
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import (
    Blueprint, render_template, request,
    jsonify, send_file, session, redirect, url_for, flash
)
from datetime import datetime
from core.gemini_client       import analyze_idea
from core.market_researcher   import get_market_data
from core.competitor_analyzer import get_competitors
from core.ecommerce_scraper   import get_ecommerce_data
from core.sales_predictor     import predict_sales
from core.niche_identifier    import identify_niches
from core.report_generator    import generate_pdf
from core.email_sender        import send_report
from database.db              import (
    save_research, get_history, get_research_by_id,
    create_user, get_user_by_email, verify_password,
    get_user_by_id, delete_research
)

main = Blueprint("main", __name__)


# ── CACHE ─────────────────────────────────────────────────────
_cache = {}

def get_cached(idea):
    key = idea.strip().lower()
    if key in _cache:
        print(f"Route cache hit: {idea}")
        return _cache[key]
    return None

def set_cache(idea, results):
    key = idea.strip().lower()
    if len(_cache) >= 50:
        del _cache[next(iter(_cache))]
    _cache[key] = results


# ── LOGIN REQUIRED ────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue", "warning")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated


# ── 1. INTRO ──────────────────────────────────────────────────
@main.route("/intro")
def intro():
    if "user_id" in session:
        return redirect(url_for("main.index"))
    return render_template("intro.html")


# ── 2. LOGIN ──────────────────────────────────────────────────
@main.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please fill in all fields", "danger")
            return redirect(url_for("main.login"))

        user = get_user_by_email(email)

        if not user:
            flash("No account found with that email", "danger")
            return redirect(url_for("main.login"))

        if not verify_password(password, user["password"]):
            flash("Incorrect password", "danger")
            return redirect(url_for("main.login"))

        session["user_id"]    = user["id"]
        session["user_name"]  = user["name"]
        session["user_email"] = user["email"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("main.index"))

    return render_template("login.html")


# ── 3. REGISTER ───────────────────────────────────────────────
@main.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name  = request.form.get("last_name",  "").strip()
        name       = f"{first_name} {last_name}".strip()
        email      = request.form.get("email",    "").strip()
        password   = request.form.get("password", "")
        confirm    = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please fill in all fields", "danger")
            return redirect(url_for("main.register"))

        if password != confirm:
            flash("Passwords do not match", "danger")
            return redirect(url_for("main.register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return redirect(url_for("main.register"))

        if get_user_by_email(email):
            flash("An account with that email already exists", "danger")
            return redirect(url_for("main.login"))

        user_id = create_user(name, email, password)

        if user_id:
            session["user_id"]    = user_id
            session["user_name"]  = name
            session["user_email"] = email
            flash(f"Welcome to MarketMind AI, {first_name}!", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Registration failed. Please try again.", "danger")
            return redirect(url_for("main.register"))

    return render_template("register.html")


# ── 4. LOGOUT ─────────────────────────────────────────────────
@main.route("/logout")
def logout():
    name = session.get("user_name", "")
    session.clear()
    flash(f"Goodbye {name}! See you soon.", "info")
    return redirect(url_for("main.intro"))


# ── 5. HOME ───────────────────────────────────────────────────
@main.route("/")
@login_required
def index():
    return render_template("index.html")


# ── 6. ANALYZE ────────────────────────────────────────────────
@main.route("/analyze", methods=["POST"])
@login_required
def analyze():
    idea = request.form.get("idea", "").strip()

    if not idea:
        return jsonify({"error": "Please enter a business idea"}), 400

    cached = get_cached(idea)
    if cached:
        cached["from_cache"] = True
        return render_template("dashboard.html", results=cached)

    try:
        pipeline = {}

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
                    print(f"{key} complete")
                except Exception as e:
                    print(f"{key} failed: {e}")
                    pipeline[key] = None

        market_data                = pipeline.get("market_data") or {}
        pipeline["sales_forecast"] = predict_sales(market_data)
        pipeline["niches"]         = identify_niches(idea, market_data)

    except Exception as e:
        print(f"Pipeline error: {e}")
        pipeline = {}

    results = {
        "idea"          : idea,
        "ai_insights"   : pipeline.get("ai_insights")    or _fallback_ai(),
        "market_data"   : pipeline.get("market_data")    or _fallback_market(),
        "competitors"   : pipeline.get("competitors")    or [],
        "ecommerce"     : pipeline.get("ecommerce")      or {},
        "sales_forecast": pipeline.get("sales_forecast") or _fallback_sales(),
        "niches"        : pipeline.get("niches")         or [],
        "created_at"    : datetime.now().strftime("%B %d, %Y %H:%M"),
        "from_cache"    : False
    }

    set_cache(idea, results)

    try:
        save_research(results, session.get("user_id"))
    except Exception as e:
        print(f"DB save error: {e}")

    return render_template("dashboard.html", results=results)


# ── FALLBACK HELPERS ──────────────────────────────────────────
def _fallback_ai():
    return {
        "summary": "Analysis temporarily unavailable.", "target_market": "General consumers",
        "verdict": "GO", "verdict_reason": "Please retry for full analysis",
        "recommendations": [], "key_risks": [],
        "pricing": {"budget": "N/A", "mid": "N/A", "premium": "N/A"},
        "competition_level": "Medium", "profit_potential": "Medium", "market_size": "N/A"
    }

def _fallback_market():
    return {
        "market_size": "N/A", "competition_level": "Medium", "profit_potential": "Medium",
        "trend_score": 5, "trends": {"dates": [], "values": []}, "trends_summary": ""
    }

def _fallback_sales():
    return {
        "months": [], "revenue": [], "trend": [],
        "total_year": 0, "peak_month": "N/A", "growth_rate": "N/A", "summary": ""
    }


# ── 7. DASHBOARD ──────────────────────────────────────────────
@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ── 8. REPORT ─────────────────────────────────────────────────
@main.route("/report", methods=["POST"])
@login_required
def report():
    try:
        idea     = request.form.get("idea")
        results  = json.loads(request.form.get("results"))
        pdf_path = generate_pdf(idea, results)
        if pdf_path:
            return jsonify({"pdf_path": pdf_path, "success": True})
        return jsonify({"error": "PDF generation failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 9. DOWNLOAD ───────────────────────────────────────────────
@main.route("/download/<path:filepath>")
@login_required
def download(filepath):
    try:
        return send_file(
            os.path.join(os.getcwd(), filepath),
            as_attachment=True,
            download_name="MarketMind_Report.pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# ── 10. EMAIL ─────────────────────────────────────────────────
@main.route("/email", methods=["POST"])
@login_required
def email_report():
    try:
        recipient = request.form.get("email")
        idea      = request.form.get("idea")
        results   = json.loads(request.form.get("results"))
        pdf_path  = generate_pdf(idea, results)
        success   = send_report(recipient, idea, pdf_path, results)
        if success:
            return jsonify({"success": True})
        return jsonify({"error": "Email failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 11. HISTORY ───────────────────────────────────────────────
@main.route("/history")
@login_required
def history():
    try:
        past = get_history(session.get("user_id"))
    except Exception as e:
        print(f"History error: {e}")
        past = []
    return render_template("history.html", research=past)


# ── 12. VIEW RESEARCH ─────────────────────────────────────────
@main.route("/history/<int:research_id>")
@login_required
def view_research(research_id):
    try:
        results = get_research_by_id(research_id)
        if not results:
            return render_template("history.html", research=[], error="Research not found")
        return render_template("dashboard.html", results=results)
    except Exception as e:
        print(f"View error: {e}")
        return render_template("history.html", research=[])


# ── 13. DELETE RESEARCH ───────────────────────────────────────
@main.route("/history/delete/<int:research_id>", methods=["POST"])
@login_required
def delete_research_route(research_id):
    try:
        delete_research(research_id)
        flash("Research deleted", "success")
    except Exception as e:
        flash("Could not delete research", "danger")
    return redirect(url_for("main.history"))


# ── 14. TERMS & CONDITIONS ────────────────────────────────────
@main.route("/terms")
def terms():
    return render_template("terms.html")


# ── 15. ABOUT ─────────────────────────────────────────────────
@main.route("/about")
def about():
    return render_template("about.html")


# ── 16. CACHE STATUS ──────────────────────────────────────────
@main.route("/cache")
def cache_status():
    return jsonify({"cached_ideas": list(_cache.keys()), "total": len(_cache)})


# ── 17. CLEAR CACHE ───────────────────────────────────────────
@main.route("/cache/clear")
def clear_cache():
    count = len(_cache)
    _cache.clear()
    return jsonify({"success": True, "cleared": count})


# ── 18. API ───────────────────────────────────────────────────
@main.route("/api/analyze", methods=["POST"])
def api_analyze():
    idea = request.json.get("idea")
    return jsonify(analyze_idea(idea))