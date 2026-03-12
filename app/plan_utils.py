# ============================================================
# APP/PLAN_UTILS.PY — Plan checking helpers
# ============================================================
# Used by routes.py to check limits before running analyses.
# Clean separation so adding new tiers is one line change.
# ============================================================

from config import Config
from database.db import get_user_usage


def get_plan_config(plan: str) -> dict:
    return Config.PLANS.get(plan, Config.PLANS["free"])


def can_analyse(user_id: int) -> tuple[bool, str]:
    """
    Returns (allowed: bool, reason: str)
    reason is empty string if allowed.
    """
    usage  = get_user_usage(user_id)
    plan   = usage.get("plan", "free")
    config = get_plan_config(plan)
    limit  = config.get("analyses_per_month")

    if limit is None:
        return True, ""   # unlimited plan

    used = usage.get("analyses_this_month", 0)
    if used >= limit:
        return False, f"You've used {used}/{limit} free analyses this month. Upgrade for unlimited access."

    return True, ""


def can_download_pdf(plan: str) -> bool:
    return get_plan_config(plan).get("pdf", False)


def can_email_report(plan: str) -> bool:
    return get_plan_config(plan).get("email_report", False)


def get_history_limit(plan: str) -> int | None:
    return get_plan_config(plan).get("history_limit")


def get_analyses_remaining(user_id: int) -> str:
    """Human-readable string like '2 of 3 remaining' or 'Unlimited'."""
    usage  = get_user_usage(user_id)
    plan   = usage.get("plan", "free")
    config = get_plan_config(plan)
    limit  = config.get("analyses_per_month")

    if limit is None:
        return "Unlimited"

    used      = usage.get("analyses_this_month", 0)
    remaining = max(0, limit - used)
    return f"{remaining} of {limit} remaining this month"
