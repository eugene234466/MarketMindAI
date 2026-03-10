# ============================================================
# CONFIG.PY — App Configuration
# SerpAPI removed — using free alternatives
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Flask ─────────────────────────────────────────────────
    SECRET_KEY         = os.getenv("FLASK_SECRET_KEY", "marketmind-secret-key-2026")
    ENV                = os.getenv("FLASK_ENV", "development")
    DEBUG              = True

    # ── Base URL for emails (Railway URL) ────────────────────
    BASE_URL           = os.getenv("BASE_URL", "http://localhost:5000")

    # ── Gemini AI ─────────────────────────────────────────────
    GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")

    # ── Google OAuth ──────────────────────────────────────────
    GOOGLE_CLIENT_ID   = os.getenv("GOOGLE_CLIENT_ID", "")

    # ── Email ─────────────────────────────────────────────────
    EMAIL_ADDRESS      = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD     = os.getenv("EMAIL_PASSWORD", "")
    SMTP_SERVER        = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT          = int(os.getenv("SMTP_PORT", 587))

    # ── Database ──────────────────────────────────────────────
    DATABASE_PATH      = "database/research_history.db"

    # ── File Paths ────────────────────────────────────────────
    REPORTS_FOLDER     = "reports"
    RAW_DATA_FOLDER    = "data/raw"
    PROCESSED_FOLDER   = "data/processed"
