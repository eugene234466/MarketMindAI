# ============================================================
# APP/ROUTES.PY — All URL Routes (with job_id support)
# ============================================================
import os
import json
import uuid
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
from app.cache import get_cached, set_cache

main = Blueprint("main", __name__)

# ── AUTH DECORATOR ──────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue", "warning")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated

# ── 1. INTRO ─────────────────────────────────────────────────
@main.route("/intro")
def intro():
    if "user_id" in session:
        return redirect(url_for("main.index"))
    return render_template("intro.html")

# ── 2. LOGIN ─────────────────────────────────────────────────
@main.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please fill in all fields", "danger")
            return redirect(url_for("main.login"))

        user = get_user_by_email(email)
        if not user or not verify_password(password, user["password"]):
            flash("Invalid email or password", "danger")
            return redirect(url_for("main.login"))

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("main.index"))

    return render_template("login.html")

# ── 3. REGISTER ──────────────────────────────────────────────
@main.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        name = f"{first_name} {last_name}".strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

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
            flash("Email already registered", "danger")
            return redirect(url_for("main.login"))

        user_id = create_user(name, email, password)
        session["user_id"] = user_id
        session["user_name"] = name
        session["user_email"] = email
        flash(f"Welcome to MarketMind AI, {first_name}!", "success")
        return redirect(url_for("main.index"))

    return render_template("register.html")

# ── 4. LOGOUT ────────────────────────────────────────────────
@main.route("/logout")
def logout():
    name = session.get("user_name", "")
    session.clear()
    flash(f"Goodbye {name}! See you soon.", "info")
    return redirect(url_for("main.intro"))

# ── 5. HOME ─────────────────────────────────────────────────
@main.route("/")
@login_required
def index():
    return render_template("index.html")

# ── 6. ANALYZE — returns job_id immediately ───────────────────
@main.route("/analyze", methods=["POST"])
@login_required
def analyze():
    idea = request.form.get("idea", "").strip()
    if not idea:
        return jsonify({"error": "No idea provided"}), 400

    job_id = str(uuid.uuid4())

    # Cache hit
    cached = get_cached(idea)
    if cached:
        cached["from_cache"] = True
        research_id = save_research(cached, session["user_id"])
        return jsonify({
            "success": True,
            "job_id": job_id,
            "research_id": research_id,
            "from_cache": True
        })

    # Store for AJAX pipeline
    session["pending_idea"] = idea
    session["pending_job_id"] = job_id

    return jsonify({"success": True, "job_id": job_id})

# ── 7. ANALYZE/RUN — AJAX call ───────────────────────────────
@main.route("/analyze/run", methods=["POST"])
@login_required
def analyze_run():
    from core.analyze import run_pipeline

    data = request.get_json(silent=True) or {}
    idea = data.get("idea") or session.pop("pending_idea", "")
    job_id = data.get("job_id") or session.pop("pending_job_id", str(uuid.uuid4()))

    if not idea:
        return jsonify({"error": "No idea provided"}), 400

    try:
        results = run_pipeline(idea)
        set_cache(idea, results)
        research_id = save_research(results, session["user_id"])
        return jsonify({"success": True, "job_id": job_id, "research_id": research_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 8. DASHBOARD & HISTORY ──────────────────────────────────
@main.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.history"))

@main.route("/history")
@login_required
def history():
    try:
        past_research = get_history(session["user_id"])
    except Exception:
        past_research = []
    return render_template("history.html", research=past_research)

@main.route("/history/<int:research_id>")
@login_required
def view_research(research_id):
    results = get_research_by_id(research_id)
    if not results:
        flash("Research not found", "warning")
        return redirect(url_for("main.history"))
    return render_template("dashboard.html", results=results)

@main.route("/history/delete/<int:research_id>", methods=["POST"])
@login_required
def delete_research_route(research_id):
    try:
        delete_research(research_id)
        flash("Research deleted successfully", "success")
    except Exception:
        flash("Could not delete research", "danger")
    return redirect(url_for("main.history"))

# ── 9. REPORTS & DOWNLOAD ───────────────────────────────────
@main.route("/report", methods=["POST"])
@login_required
def report():
    from core.report_generator import generate_pdf
    idea = request.form.get("idea")
    results = json.loads(request.form.get("results", "{}"))
    pdf_path = generate_pdf(idea, results)
    if pdf_path:
        return jsonify({"pdf_path": pdf_path, "success": True})
    return jsonify({"error": "PDF generation failed"}), 500

@main.route("/download/<path:filepath>")
@login_required
def download(filepath):
    abs_path = os.path.join(os.getcwd(), filepath)
    return send_file(abs_path, as_attachment=True, download_name="MarketMind_Report.pdf")

# ── 10. CACHE STATUS ─────────────────────────────────────────
@main.route("/cache")
def cache_status():
    return jsonify({"cached_ideas": list(_cache.keys()), "total_cached": len(_cache), "max_cache": 50})

@main.route("/cache/clear")
def clear_cache_route():
    count = len(_cache)
    _cache.clear()
    return jsonify({"success": True, "cleared": count})
