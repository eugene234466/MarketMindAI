# ============================================================
# MAIN.PY — Production Entry Point
# ============================================================

import os
from app import create_app

app = create_app()

# Initialise PostgreSQL tables on startup
with app.app_context():
    try:
        from database.db import init_db
        init_db()
    except Exception as e:
        print(f"[Startup] DB init warning: {e}")

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
