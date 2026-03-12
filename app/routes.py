# ============================================================
# APP/ROUTES.PY — All URL Routes
# ============================================================
# /analyze      POST  → shows loading screen, stores idea in session
# /analyze/run  POST  → AJAX — runs pipeline, saves to DB, returns JSON
# /history/<id>       → renders dashboard for a saved research ID
# ============================================================

import os
import json
from functools import wraps
from flask import (
    Blueprint, render_template, request,
    jsonify, send_file, session, redirect, url_for, flash
)

from database.db import (
    save_research, get_history, get_research_by_id,
    create_user, get_user_by_email, verify_password,
    get_user_by_id, delete_research
)


# ── BLUEPRINT ─────────────────────────────────────────────────────────────────
main = Blueprint("main", __name__)


# ── IN-MEMORY ROUTE CACHE (50 slots, LRU-style) ───────────────────────────────
_cache: dict = {}

def get_cached(idea: str):
    return _cache.get(idea.strip().lower())

def set_cache(idea: str, results: dict):
    key = idea.strip().lower()
    if len(_cache) >= 50:
        del _cache[next(iter(_cache))]
    _cache[key] = results


# ── AUTH DECORATOR ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue", "warning")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated


# ── 1. INTRO ──────────────────────────────────────────────────────────────────
@main.route("/intro")
def intro():
    if "user_id" in session:
        return redirect(url_for("main.index"))
    return render_template("intro.html")


# ── 2. LOGIN ──────────────────────────────────────────────────────────────────
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


# ── 3. REGISTER ───────────────────────────────────────────────────────────────
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


# ── 4. LOGOUT ─────────────────────────────────────────────────────────────────
@main.route("/logout")
def logout():
    name = session.get("user_name", "")
    session.clear()
    flash(f"Goodbye {name}! See you soon.", "info")
    return redirect(url_for("main.intro"))


# ── 5. HOME ───────────────────────────────────────────────────────────────────
@main.route("/")
@login_required
def index():
    return render_template("index.html")


# ── 6. ANALYZE — shows loading screen ────────────────────────────────────────
@main.route("/analyze", methods=["POST"])
@login_required
def analyze():
    idea = request.form.get("idea", "").strip()

    if not idea:
        flash("Please enter a business idea", "danger")
        return redirect(url_for("main.index"))

    # Cache hit — skip loading screen, go straight to saved result
    cached = get_cached(idea)
    if cached:
        cached["from_cache"] = True
        research_id = save_research(cached, session["user_id"])
        if research_id:
            return redirect(url_for("main.view_research", research_id=research_id))

    # Store idea in session for the AJAX call to pick up
    session["pending_idea"] = idea

    # Render loading screen — it will POST to /analyze/run
    return render_template("loading.html", idea=idea)


# ── 7. ANALYZE/RUN — AJAX called by loading screen ───────────────────────────
@main.route("/analyze/run", methods=["POST"])
@login_required
def analyze_run():
    """
    Called via fetch() from loading.html.
    Runs heavy pipeline, saves to Postgres, returns { research_id }.
    """
    from core.analyze import run_pipeline

    data = request.get_json(silent=True) or {}
    idea = data.get("idea") or session.pop("pending_idea", "")

    if not idea:
        return jsonify({"error": "No idea provided"}), 400

    try:
        results     = run_pipeline(idea)
        set_cache(idea, results)
        research_id = save_research(results, session["user_id"])

        return jsonify({"success": True, "research_id": research_id})

    except Exception as e:
        print(f"[analyze_run] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 8. DASHBOARD — redirect to history if accessed directly ──────────────────
@main.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.history"))


# ── 9. REPORT (generate PDF) ─────────────────────────────────────────────────
@main.route("/report", methods=["POST"])
@login_required
def report():
    try:
        from core.report_generator import generate_pdf
        idea     = request.form.get("idea")
        results  = json.loads(request.form.get("results", "{}"))
        pdf_path = generate_pdf(idea, results)

        if pdf_path:
            return jsonify({"pdf_path": pdf_path, "success": True})
        return jsonify({"error": "PDF generation failed"}), 500

    except Exception as e:
        print(f"[report] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 10. DOWNLOAD PDF ──────────────────────────────────────────────────────────
@main.route("/download/<path:filepath>")
@login_required
def download(filepath):
    try:
        abs_path = os.path.join(os.getcwd(), filepath)
        return send_file(abs_path, as_attachment=True, download_name="MarketMind_Report.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# ── 11. EMAIL ─────────────────────────────────────────────────────────────────
@main.route("/email", methods=["POST"])
@login_required
def email_report():
    try:
        from core.report_generator import generate_pdf
        from core.email_sender     import send_report

        recipient = request.form.get("email")
        idea      = request.form.get("idea")
        results   = json.loads(request.form.get("results", "{}"))
        pdf_path  = generate_pdf(idea, results)
        success   = send_report(recipient, idea, pdf_path, results)

        return jsonify({"success": True} if success else {"error": "Email failed"}), 200 if success else 500

    except Exception as e:
        print(f"[email] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 12. HISTORY ───────────────────────────────────────────────────────────────
@main.route("/history")
@login_required
def history():
    try:
        past_research = get_history(session["user_id"])
    except Exception as e:
        print(f"[history] Error: {e}")
        past_research = []
    return render_template("history.html", research=past_research)


# ── 13. VIEW SINGLE RESEARCH ──────────────────────────────────────────────────
@main.route("/history/<int:research_id>")
@login_required
def view_research(research_id):
    try:
        results = get_research_by_id(research_id)
        if not results:
            flash("Research not found", "warning")
            return redirect(url_for("main.history"))
        return render_template("dashboard.html", results=results)
    except Exception as e:
        print(f"[view_research] Error: {e}")
        return redirect(url_for("main.history"))


# ── 14. DELETE RESEARCH ───────────────────────────────────────────────────────
@main.route("/history/delete/<int:research_id>", methods=["POST"])
@login_required
def delete_research_route(research_id):
    try:
        delete_research(research_id)
        flash("Research deleted successfully", "success")
    except Exception as e:
        print(f"[delete] Error: {e}")
        flash("Could not delete research", "danger")
    return redirect(url_for("main.history"))


# ── 15. TERMS ─────────────────────────────────────────────────────────────────
@main.route("/terms")
def terms():
    return render_template("terms.html")


# ── 16. ABOUT ─────────────────────────────────────────────────────────────────
@main.route("/about")
def about():
    return render_template("about.html")


# ── 17. CACHE STATUS ─────────────────────────────────────────────────────────
@main.route("/cache")
def cache_status():
    return jsonify({"cached_ideas": list(_cache.keys()), "total_cached": len(_cache), "max_cache": 50})


# ── 18. CLEAR CACHE ───────────────────────────────────────────────────────────
@main.route("/cache/clear")
def clear_cache():
    count = len(_cache)
    _cache.clear()
    return jsonify({"success": True, "cleared": count})


# ── 19. API ───────────────────────────────────────────────────────────────────
@main.route("/api/analyze", methods=["POST"])
def api_analyze():
    from core.analyze import run_pipeline
    idea    = (request.json or {}).get("idea", "")
    results = run_pipeline(idea)
    return jsonify(results)
