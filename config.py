# ============================================================
# CONFIG.PY
# ============================================================
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # ── Flask ──────────────────────────────────────────────
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "marketmind-secret-key-2026")
    ENV        = os.getenv("FLASK_ENV", "production")
    DEBUG      = ENV == "development"

    # ── AI ─────────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # ── Database ───────────────────────────────────────────
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # ── Email ──────────────────────────────────────────────
    EMAIL_ADDRESS  = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    SMTP_SERVER    = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))

    # ── Paths ──────────────────────────────────────────────
    REPORTS_FOLDER = "reports"
