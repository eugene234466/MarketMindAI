# ============================================================
# APP/ROUTES.PY
# ============================================================
import os
import json
import uuid
import threading
from functools import wraps
from flask import (
    Blueprint, render_template, request, jsonify,
    send_file, session, redirect, url_for, flash, abort
)
from config import Config
from database.db import (
    save_research, get_history, get_research_by_id,
    create_user, get_user_by_email, verify_password, get_user_by_id,
    delete_research, create_job, complete_job, fail_job, get_job, delete_job,
    increment_usage,
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
    return render_template("index.html")


# ── 6. ANALYZE ────────────────────────────────────────────────
@main.route("/analyze", methods=["POST"])
@login_required
def analyze():
    idea    = request.form.get("idea", "").strip()
    user_id = session["user_id"]

    if not idea:
        flash("Please enter a business idea", "danger")
        return redirect(url_for("main.index"))

    # Cache hit — save and redirect immediately
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
    try:
        data    = request.get_json(silent=True) or {}
        idea    = data.get("idea") or session.pop("pending_idea", "")
        user_id = session["user_id"]

        if not idea:
            return jsonify({"error": "No idea provided"}), 400

        job_id = str(uuid.uuid4())
        create_job(job_id)

        def run(idea, user_id, job_id):
            error_msg = None
            try:
                from core.analyze import run_pipeline
                results     = run_pipeline(idea)
                set_cache(idea, results)
                research_id = save_research(results, user_id)
                increment_usage(user_id)
                complete_job(job_id, research_id)
                return
            except Exception as e:
                import traceback; traceback.print_exc()
                error_msg = str(e) or "Unknown pipeline error"

            # Guaranteed fail path — retry fail_job up to 3 times
            for attempt in range(3):
                try:
                    fail_job(job_id, error_msg)
                    return
                except Exception as fe:
                    print(f"[job {job_id}] fail_job attempt {attempt+1} error: {fe}")
                    import time; time.sleep(1)
            print(f"[job {job_id}] Could not write failure to DB after 3 attempts")

        threading.Thread(target=run, args=(idea, user_id, job_id), daemon=True).start()
        return jsonify({"job_id": job_id})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# ── 8. ANALYZE/STATUS ─────────────────────────────────────────
@main.route("/analyze/status/<job_id>")
@login_required
def analyze_status(job_id):
    job = get_job(job_id)

    # DB hiccup — return pending so the frontend keeps polling
    if job is None:
        return jsonify({"status": "pending"})

    if job["status"] == "done":
        delete_job(job_id)
        return jsonify({"status": "done", "research_id": job["research_id"]})

    if job["status"] == "error":
        err = job.get("error") or "Analysis failed — please try again"
        delete_job(job_id)
        return jsonify({"status": "error", "error": err})

    # Check for stale jobs (pending > 5 min = thread died silently)
   created_at = job.get("created_at")
   if created_at:
    from datetime import datetime, timezone, timedelta
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - created_at
    if age > timedelta(minutes=5):
        delete_job(job_id)
        return jsonify({"status": "error", "error": "Analysis timed out — please try again"})


# ── 9. DASHBOARD ──────────────────────────────────────────────
@main.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.history"))


# ── 10. REPORT (PDF) ──────────────────────────────────────────
@main.route("/report", methods=["POST"])
@login_required
def report():
    try:
        from core.report_generator import generate_pdf
        idea    = request.form.get("idea", "")
        results = json.loads(request.form.get("results", "{}"))
        path    = generate_pdf(idea, results)
        if not path:
            return jsonify({"error": "PDF generation failed"}), 500
        # Store just the filename — the download route resolves the full path
        filename = os.path.basename(path)
        return jsonify({"pdf_path": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 10b. DOWNLOAD PDF ─────────────────────────────────────────
@main.route("/download/<filename>")
@login_required
def download_pdf(filename):
    # Sanitise — allow only safe filenames
    import re
    if not re.match(r'^MarketMind_[\w\-]+\.pdf$', filename):
        abort(404)
    reports_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports"))
    filepath = os.path.join(reports_dir, filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_file(filepath, as_attachment=True,
                     download_name=filename,
                     mimetype="application/pdf")


# ── 11. NICHE ─────────────────────────────────────────────────
@main.route("/niche/<int:research_id>")
@login_required
def niche_detail(research_id):
    try:
        results = get_research_by_id(research_id)
        if not results:
            abort(404)
        return jsonify(results.get("niche_opportunities", {}))
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# ── 12. EMAIL ─────────────────────────────────────────────────
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


# ── 13. HISTORY ───────────────────────────────────────────────
@main.route("/history")
@login_required
def history():
    try:
        past = get_history(session["user_id"], limit=50)
    except Exception:
        past = []
    return render_template("history.html", research=past)


# ── 14. VIEW RESEARCH ─────────────────────────────────────────
@main.route("/history/<int:research_id>")
@login_required
def view_research(research_id):
    try:
        results = get_research_by_id(research_id)
        if not results:
            flash("Research not found", "warning")
            return redirect(url_for("main.history"))
        return render_template("dashboard.html", results=results,
                               can_pdf=True, can_email=True)
    except Exception as e:
        print(f"[view_research] {e}")
        return redirect(url_for("main.history"))


# ── 15. DELETE RESEARCH ───────────────────────────────────────
@main.route("/history/delete/<int:research_id>", methods=["POST"])
@login_required
def delete_research_route(research_id):
    try:
        delete_research(research_id)
        flash("Research deleted", "success")
    except Exception:
        flash("Could not delete research", "danger")
    return redirect(url_for("main.history"))


# ── 16. HEALTH CHECK ──────────────────────────────────────────
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


# ── FORGOT PASSWORD ──────────────────────────────────────────
@main.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "user_id" in session:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        msg = "If that email is registered, you\'ll receive a reset link shortly."
        user = get_user_by_email(email)
        if user:
            import secrets
            from database.db import create_reset_token
            from core.email_sender import send_reset_email
            token     = secrets.token_urlsafe(32)
            reset_url = request.host_url.rstrip("/") + url_for("main.reset_password", token=token)
            create_reset_token(user["id"], token)
            send_reset_email(email, reset_url)
        flash(msg, "info")
        return redirect(url_for("main.forgot_password"))
    return render_template("forgot_password.html")


# ── RESET PASSWORD ────────────────────────────────────────────
@main.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if "user_id" in session:
        return redirect(url_for("main.index"))
    from database.db import get_reset_token, delete_reset_token, update_password
    row = get_reset_token(token)
    if not row:
        flash("This reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for("main.forgot_password"))
    if request.method == "POST":
        pw  = request.form.get("password", "")
        pw2 = request.form.get("confirm_password", "")
        if len(pw) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("reset_password.html", token=token)
        if pw != pw2:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)
        update_password(row["user_id"], pw)
        delete_reset_token(token)
        flash("Password updated! You can now log in.", "success")
        return redirect(url_for("main.login"))
    return render_template("reset_password.html", token=token)


# ── 17. TERMS / ABOUT / MISC ──────────────────────────────────
@main.route("/terms")
def terms():
    return render_template("terms.html")

@main.route("/about")
def about():
    return render_template("about.html")

@main.route("/cache")
def cache_status():
    return jsonify(cache_info())

@main.route("/cache/clear")
def clear_cache_route():
    count = clear_cache()
    return jsonify({"success": True, "cleared": count})

@main.route("/api/analyze", methods=["POST"])
def api_analyze():
    from core.analyze import run_pipeline
    idea = (request.json or {}).get("idea", "")
    return jsonify(run_pipeline(idea))
