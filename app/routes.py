# ============================================================
# APP/ROUTES.PY — All URL Routes
# ============================================================
# /analyze      POST  → shows loading screen
# /analyze/run  POST  → starts background thread, returns job_id immediately
# /analyze/status/<job_id> GET → poll for completion
# /history/<id>       → renders dashboard
# ============================================================

import os
import json
import uuid
import threading
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

main = Blueprint("main", __name__)

# ── IN-MEMORY CACHES ──────────────────────────────────────────────────────────
_cache: dict = {}   # idea -> results
_jobs: dict  = {}   # job_id -> { status, research_id, error }

def get_cached(idea):
    return _cache.get(idea.strip().lower())

def set_cache(idea, results):
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


# ── 6. ANALYZE — show loading screen ─────────────────────────────────────────
@main.route("/analyze", methods=["POST"])
@login_required
def analyze():
    idea = request.form.get("idea", "").strip()

    if not idea:
        flash("Please enter a business idea", "danger")
        return redirect(url_for("main.index"))

    # Cache hit — skip loading screen entirely
    cached = get_cached(idea)
    if cached:
        cached["from_cache"] = True
        research_id = save_research(cached, session["user_id"])
        if research_id:
            return redirect(url_for("main.view_research", research_id=research_id))

    session["pending_idea"] = idea
    return render_template("loading.html", idea=idea)


# ── 7. ANALYZE/RUN — starts background thread, returns job_id instantly ───────
@main.route("/analyze/run", methods=["POST"])
@login_required
def analyze_run():
    """
    Returns a job_id within milliseconds.
    The actual pipeline runs in a daemon thread.
    The loading screen polls /analyze/status/<job_id>.
    """
    data    = request.get_json(silent=True) or {}
    idea    = data.get("idea") or session.pop("pending_idea", "")
    user_id = session["user_id"]

    if not idea:
        return jsonify({"error": "No idea provided"}), 400

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "research_id": None, "error": None}

    def run(idea, user_id, job_id):
        try:
            from core.analyze import run_pipeline
            results     = run_pipeline(idea)
            set_cache(idea, results)
            research_id = save_research(results, user_id)
            _jobs[job_id] = {"status": "done", "research_id": research_id, "error": None}
        except Exception as e:
            print(f"[job {job_id}] Error: {e}")
            _jobs[job_id] = {"status": "error", "research_id": None, "error": str(e)}

    t = threading.Thread(target=run, args=(idea, user_id, job_id), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


# ── 8. ANALYZE/STATUS — polled by loading screen ──────────────────────────────
@main.route("/analyze/status/<job_id>")
@login_required
def analyze_status(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"status": "error", "error": "Job not found"}), 404

    if job["status"] == "done":
        # Clean up job slot
        _jobs.pop(job_id, None)
        return jsonify({"status": "done", "research_id": job["research_id"]})
    elif job["status"] == "error":
        _jobs.pop(job_id, None)
        return jsonify({"status": "error", "error": job["error"]}), 500
    else:
        return jsonify({"status": "pending"})


# ── 9. DASHBOARD ──────────────────────────────────────────────────────────────
@main.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.history"))


# ── 10. REPORT ────────────────────────────────────────────────────────────────
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
        return jsonify({"error": str(e)}), 500


# ── 11. DOWNLOAD ──────────────────────────────────────────────────────────────
@main.route("/download/<path:filepath>")
@login_required
def download(filepath):
    try:
        abs_path = os.path.join(os.getcwd(), filepath)
        return send_file(abs_path, as_attachment=True, download_name="MarketMind_Report.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# ── 12. EMAIL ─────────────────────────────────────────────────────────────────
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
        return jsonify({"error": str(e)}), 500


# ── 13. HISTORY ───────────────────────────────────────────────────────────────
@main.route("/history")
@login_required
def history():
    try:
        past_research = get_history(session["user_id"])
    except Exception as e:
        print(f"[history] {e}")
        past_research = []
    return render_template("history.html", research=past_research)


# ── 14. VIEW RESEARCH ─────────────────────────────────────────────────────────
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
        print(f"[view_research] {e}")
        return redirect(url_for("main.history"))


# ── 15. DELETE RESEARCH ───────────────────────────────────────────────────────
@main.route("/history/delete/<int:research_id>", methods=["POST"])
@login_required
def delete_research_route(research_id):
    try:
        delete_research(research_id)
        flash("Research deleted successfully", "success")
    except Exception as e:
        flash("Could not delete research", "danger")
    return redirect(url_for("main.history"))


# ── 16. TERMS ─────────────────────────────────────────────────────────────────
@main.route("/terms")
def terms():
    return render_template("terms.html")


# ── 17. ABOUT ─────────────────────────────────────────────────────────────────
@main.route("/about")
def about():
    return render_template("about.html")


# ── 18. CACHE STATUS ──────────────────────────────────────────────────────────
@main.route("/cache")
def cache_status():
    return jsonify({"cached_ideas": list(_cache.keys()), "total_cached": len(_cache), "max_cache": 50})


# ── 19. CLEAR CACHE ───────────────────────────────────────────────────────────
@main.route("/cache/clear")
def clear_cache():
    count = len(_cache)
    _cache.clear()
    return jsonify({"success": True, "cleared": count})


# ── 20. API ───────────────────────────────────────────────────────────────────
@main.route("/api/analyze", methods=["POST"])
def api_analyze():
    from core.analyze import run_pipeline
    idea    = (request.json or {}).get("idea", "")
    results = run_pipeline(idea)
    return jsonify(results)
