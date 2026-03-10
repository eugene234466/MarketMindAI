# ============================================================
# APP/__INIT__.PY — Flask App Factory
# Updated for PostgreSQL + Async Analysis
# ============================================================

from flask import Flask
from config import Config


def create_app():

    # ── STEP 1: CREATE APP ──────────────────────────────────
    # Creates the Flask application instance
    app = Flask(__name__)


    # ── STEP 2: LOAD CONFIG ─────────────────────────────────
    # Pulls all settings from config.py
    app.config.from_object(Config)


    # ── STEP 3: INIT DATABASE ───────────────────────────────
    # Sets up PostgreSQL database & creates tables
    print("🚀 Initializing database...")
    from database.db import init_db
    init_db(app)


    # ── STEP 4: INIT BACKGROUND WORKER ──────────────────────
    # Starts the background task processor
    print("🔄 Starting background worker...")
    try:
        from core.tasks import start_worker
        start_worker()
        print("✅ Background worker started")
    except Exception as e:
        print(f"⚠️ Worker start skipped: {e}")


    # ── STEP 5: REGISTER BLUEPRINT ──────────────────────────
    # Connects all routes from routes.py to the app
    print("📡 Registering routes...")
    from app.routes import main
    app.register_blueprint(main)


    # ── STEP 6: PRINT STATUS ────────────────────────────────
    print(f"✅ App created successfully")
    print(f"🌐 Environment: {Config.ENV}")
    print(f"📊 Database: PostgreSQL")
    print(f"🤖 Gemini: {'Connected' if Config.GEMINI_API_KEY else 'No API Key'}")


    # ── STEP 7: RETURN APP ──────────────────────────────────
    return app
