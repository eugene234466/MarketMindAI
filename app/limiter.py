# ============================================================
# APP/LIMITER.PY — Rate Limiting
# ============================================================
# Uses Flask-Limiter with Redis if available, memory otherwise.
# Drop-in: just call init_limiter(app) from create_app().
# ============================================================
import os

def init_limiter(app):
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        redis_url = os.environ.get("REDIS_URL")
        storage   = f"redis://{redis_url}" if redis_url else "memory://"

        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=storage,
            default_limits=["200 per hour"],
        )

        # Attach to app for use in routes
        app.limiter = limiter
        print(f"[Limiter] Rate limiting active ({storage})")
        return limiter

    except ImportError:
        print("[Limiter] flask-limiter not installed — skipping rate limiting")
        return None


def get_limiter():
    """Returns the limiter instance attached to the current app."""
    from flask import current_app
    return getattr(current_app, "limiter", None)
