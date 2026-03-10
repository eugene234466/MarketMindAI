# ============================================================
# APP/__INIT__.PY — Flask App Factory
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
    # Sets up SQLite database & creates tables
    from database.db import init_db
    init_db(app)


    # ── STEP 4: REGISTER BLUEPRINT ──────────────────────────
    # Connects all routes from routes.py to the app
    from app.routes import main
    app.register_blueprint(main)


    # ── STEP 5: RETURN APP ──────────────────────────────────
    return app