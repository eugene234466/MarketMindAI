# ============================================================
# APP/ROUTES.PY (Subscription-Free)
# ============================================================
import os
import json
import uuid
import threading
from functools import wraps
from flask import (
    Blueprint, render_template, request, jsonify,
    send_file, session, redirect, url_for, flash
)
from database.db import (
    save_research, get_history, get_research_by_id,
    create_user, get_user_by_email, verify_password, get_user_by_id,
    delete_research, create_job, complete_job, fail_job, get_job,
    get_user_usage, increment_usage
)
from app.cache import get_cached, set_cache, clear_cache, cache_info

main = Blueprint("main", __name__)


# ── DECORATORS ────────────────────────────────────────────────
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
        if not user or not verify_password(password, user["password"]):
            flash("Incorrect email or password", "danger")
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
        first  = request.form.get("first_name", "").strip()
        last   = request.form.get("last_name",  "").strip()
        name   = f"{first} {last}".strip()
        email  = request.form.get("email",    "").strip()
        pw     = request.form.get("password", "")
        pw2    = request.form.get("confirm_password", "")
        if not name or not email or not pw:
            flash("Please fill in all fields", "danger")
            return redirect(url_for("main.register"))
        if pw != pw2:
            flash("Passwords do not match", "danger")
            return redirect(url_for("main.register"))
        if len(pw) < 6:
            flash("Password must be at least 6 characters", "danger")
            return redirect(url_for("main.register"))
        if get_user_by_email(email):
            flash("An account with that email already exists", "danger")
            return redirect(url_for("main.login"))
        user_id = create_user(name, email, pw)
        if user_id:
            session["user_id"]    = user_id
            session["user_name"]  = name
            session["user_email"] = email
            flash(f"Welcome to MarketMind AI, {first}!", "success")
            return redirect(url_for("main.index"))
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
    remaining = max(0, 5 - get_user_usage(session["user_id"]))  # hardcoded free-tier limit
    return render_template("index.html", remaining=remaining)


# ── 6. ANALYZE ────────────────────────────────────────────────
@main.route("/analyze", methods=["POST"])
@login_required
def analyze():
    idea    = request.form.get("idea", "").strip()
    user_id = session["user_id"]

    if not idea:
        flash("Please enter a business idea", "danger")
        return redirect(url_for("main.index"))

    if get_user_usage(user_id) >= 5:  # free-tier limit
        flash("You have reached the maximum analyses for free users.", "warning")
        return redirect(url_for("main.index"))

    cached = get_cached(idea)
    if cached:
        cached["from_cache"] = True
        research_id = save_research(cached, user_id)
        increment_usage(user_id)
        if research_id:
            return redirect(url_for("main.view_research", research_id=research_id))

    session["pending_idea"] = idea
    return render_template("loading.html", idea=idea)


# ── 7. ANALYZE/RUN ────────────────────────────────────────────
@main.route("/analyze/run", methods=["POST"])
@login_required
def analyze_run():
    data    = request.get_json(silent=True) or {}
    idea    = data.get("idea") or session.pop("pending_idea", "")
    user_id = session["user_id"]

    if not idea:
        return jsonify({"error": "No idea provided"}), 400

    if get_user_usage(user_id) >= 5:
        return jsonify({"error": "Analysis limit reached"}), 403

    job_id = str(uuid.uuid4())
    create_job(job_id)

    def run(idea, user_id, job_id):
        try:
            from core.analyze import run_pipeline
            results     = run_pipeline(idea)
            set_cache(idea, results)
            research_id = save_research(results, user_id)
            increment_usage(user_id)
            complete_job(job_id, research_id)
        except Exception as e:
            print(f"[job {job_id}] Error: {e}")
            fail_job(job_id, str(e))

    threading.Thread(target=run, args=(idea, user_id, job_id), daemon=True).start()
    return jsonify({"job_id": job_id})


# ── 8. ANALYZE/STATUS ─────────────────────────────────────────
@main.route("/analyze/status/<job_id>")
@login_required
def analyze_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"status": "error", "error": "Job not found"}), 404
    if job["status"] == "done":
        delete_job(job_id)
        return jsonify({"status": "done", "research_id": job["research_id"]})
    elif job["status"] == "error":
        delete_job(job_id)
        return jsonify({"status": "error", "error": job["error"]}), 500
    return jsonify({"status": "pending"})


# ── 9. DASHBOARD ──────────────────────────────────────────────
@main.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.history"))


# ── 10. HISTORY ───────────────────────────────────────────────
@main.route("/history")
@login_required
def history():
    try:
        past = get_history(session["user_id"], limit=10)
    except Exception:
        past = []
    return render_template("history.html", research=past)


# ── 11. VIEW RESEARCH ─────────────────────────────────────────
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


# ── 12. DELETE RESEARCH ───────────────────────────────────────
@main.route("/history/delete/<int:research_id>", methods=["POST"])
@login_required
def delete_research_route(research_id):
    try:
        delete_research(research_id)
        flash("Research deleted", "success")
    except Exception:
        flash("Could not delete research", "danger")
    return redirect(url_for("main.history"))


# ── 13. DOWNLOAD ──────────────────────────────────────────────
@main.route("/download/<path:filepath>")
@login_required
def download(filepath):
    try:
        return send_file(os.path.join(os.getcwd(), filepath),
                         as_attachment=True, download_name="MarketMind_Report.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# ── 14. CACHE STATUS ──────────────────────────────────────────
@main.route("/cache")
def cache_status():
    return jsonify(cache_info())


@main.route("/cache/clear")
def clear_cache_route():
    count = clear_cache()
    return jsonify({"success": True, "cleared": count})


# ── 15. HEALTH CHECK ─────────────────────────────────────────
@main.route("/health")
def health():
    try:
        from database.db import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok", "db": "ok"}, 200
    except Exception as e:
        return {"status": "error", "db": str(e)}, 500


# ── 16. TERMS / ABOUT / MISC ──────────────────────────────────
@main.route("/terms")
def terms():
    return render_template("terms.html")


@main.route("/about")
def about():
    return render_template("about.html")


# ── 17. API ANALYZE ──────────────────────────────────────────
@main.route("/api/analyze", methods=["POST"])
def api_analyze():
    from core.analyze import run_pipeline
    idea = (request.json or {}).get("idea", "")
    return jsonify(run_pipeline(idea))
