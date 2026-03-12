# ============================================================
# APP/__INIT__.PY
# ============================================================
import os
from flask import Flask
from config import Config


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config.from_object(Config)

    # ── Session hardening ─────────────────────────────────────
    app.config.update(
        SESSION_COOKIE_SECURE   = os.environ.get("FLASK_ENV") == "production",
        SESSION_COOKIE_HTTPONLY = True,
        SESSION_COOKIE_SAMESITE = "Lax",
        PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30,  # 30 days
    )

    # ── Ensure folders exist ──────────────────────────────────
    os.makedirs(app.config["REPORTS_FOLDER"], exist_ok=True)

    # ── Logging ───────────────────────────────────────────────
    from app.logger import init_logging
    init_logging(app)

    # ── Compression (gzip responses automatically) ────────────
    try:
        from flask_compress import Compress
        Compress(app)
        app.logger.info("Gzip compression enabled")
    except ImportError:
        app.logger.warning("flask-compress not installed — responses uncompressed")

    # ── Rate limiting ─────────────────────────────────────────
    from app.limiter import init_limiter
    init_limiter(app)

    # ── Blueprint ─────────────────────────────────────────────
    from app.routes import main
    app.register_blueprint(main)

    # ── Security + cache headers ──────────────────────────────
    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]         = "SAMEORIGIN"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"]        = "1; mode=block"

        ct = response.content_type or ""
        if "text/html" in ct:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        elif any(x in ct for x in ("javascript", "css", "font", "image")):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        return response

    return app
