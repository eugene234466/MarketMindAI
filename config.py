# ============================================================
# CONFIG.PY
# ============================================================
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # ── Flask ──────────────────────────────────────────────
    SECRET_KEY     = os.getenv("FLASK_SECRET_KEY", "marketmind-secret-key-2026")
    ENV            = os.getenv("FLASK_ENV", "production")
    DEBUG          = ENV == "development"

    # ── AI ─────────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # ── Database ───────────────────────────────────────────
    DATABASE_URL   = os.getenv("DATABASE_URL", "")

    # ── Email ──────────────────────────────────────────────
    EMAIL_ADDRESS  = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    SMTP_SERVER    = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))

    # ── Paths ──────────────────────────────────────────────
    REPORTS_FOLDER = "reports"

    # ── Stripe ─────────────────────────────────────────────
    STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Price IDs — create these in Stripe dashboard, paste here
    STRIPE_PRO_MONTHLY_PRICE_ID      = os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID", "")
    STRIPE_BUSINESS_MONTHLY_PRICE_ID = os.getenv("STRIPE_BUSINESS_MONTHLY_PRICE_ID", "")

    # ── Plans ──────────────────────────────────────────────
    PLANS = {
        "free": {
            "name"            : "Free",
            "price"           : 0,
            "analyses_per_month": 3,
            "pdf"             : False,
            "email_report"    : False,
            "history_limit"   : 5,
        },
        "pro": {
            "name"            : "Pro",
            "price"           : 12,
            "analyses_per_month": None,   # unlimited
            "pdf"             : True,
            "email_report"    : True,
            "history_limit"   : None,     # unlimited
        },
        "business": {
            "name"            : "Business",
            "price"           : 29,
            "analyses_per_month": None,
            "pdf"             : True,
            "email_report"    : True,
            "history_limit"   : None,
        },
    }
