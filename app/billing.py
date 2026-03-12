# ============================================================
# APP/BILLING.PY — Stripe Integration
# ============================================================
# All Stripe logic lives here. Routes.py calls these functions.
# When you're ready to go paid, just set STRIPE_* env vars.
# ============================================================

import os
from config import Config

# Stripe is optional — only imported if keys are present
def _get_stripe():
    try:
        import stripe
        stripe.api_key = Config.STRIPE_SECRET_KEY
        return stripe if Config.STRIPE_SECRET_KEY else None
    except ImportError:
        return None


def create_checkout_session(user_id: int, user_email: str, plan: str, success_url: str, cancel_url: str) -> str | None:
    """
    Creates a Stripe Checkout session for the given plan.
    Returns the checkout URL or None if Stripe isn't configured.
    """
    stripe = _get_stripe()
    if not stripe:
        return None

    price_id = (
        Config.STRIPE_PRO_MONTHLY_PRICE_ID if plan == "pro"
        else Config.STRIPE_BUSINESS_MONTHLY_PRICE_ID
    )
    if not price_id:
        return None

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": str(user_id), "plan": plan},
            subscription_data={"metadata": {"user_id": str(user_id), "plan": plan}},
        )
        return session.url
    except Exception as e:
        print(f"[Billing] create_checkout_session error: {e}")
        return None


def create_portal_session(stripe_customer_id: str, return_url: str) -> str | None:
    """
    Creates a Stripe Customer Portal session so users can manage billing.
    """
    stripe = _get_stripe()
    if not stripe or not stripe_customer_id:
        return None
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception as e:
        print(f"[Billing] create_portal_session error: {e}")
        return None


def handle_webhook(payload: bytes, sig_header: str) -> dict | None:
    """
    Validates and parses a Stripe webhook event.
    Returns the event dict or None on failure.
    """
    stripe = _get_stripe()
    if not stripe or not Config.STRIPE_WEBHOOK_SECRET:
        return None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
        return event
    except Exception as e:
        print(f"[Billing] webhook error: {e}")
        return None


def get_plan_from_price_id(price_id: str) -> str:
    if price_id == Config.STRIPE_PRO_MONTHLY_PRICE_ID:
        return "pro"
    if price_id == Config.STRIPE_BUSINESS_MONTHLY_PRICE_ID:
        return "business"
    return "free"


def is_stripe_configured() -> bool:
    return bool(Config.STRIPE_SECRET_KEY and Config.STRIPE_PUBLISHABLE_KEY)
