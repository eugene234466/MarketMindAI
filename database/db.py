# ============================================================
# DATABASE/DB.PY — PostgreSQL with Connection Pooling
# ============================================================
# Replaces SQLite3. Uses DATABASE_URL from environment.
# All functions maintain the same API so routes.py needs
# zero changes.
# ============================================================

import os
import json
import bcrypt
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager

# ── CONNECTION POOL ──────────────────────────────────────────────────────────
# Railway injects DATABASE_URL automatically when you add a Postgres plugin.
# Min 1 connection, max 10 (safe for free/starter Railway plan).

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Railway sometimes provides postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_pool: ThreadedConnectionPool = None


def get_pool() -> ThreadedConnectionPool:
    """Lazily create the connection pool on first use."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Add a PostgreSQL plugin in Railway and it will be injected automatically."
            )
        _pool = ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
        print("[DB] Connection pool created.")
    return _pool


@contextmanager
def get_conn():
    """Context manager — borrows a connection from the pool and returns it."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ── INIT TABLES ──────────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist. Call once at app startup."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    name       TEXT        NOT NULL,
                    email      TEXT UNIQUE NOT NULL,
                    password   TEXT        NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS research (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    idea       TEXT        NOT NULL,
                    results    JSONB       NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            # Index for fast history lookups per user
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_research_user_id
                ON research(user_id);
            """)
    print("[DB] Tables ready.")


# ── USER FUNCTIONS ────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> int | None:
    """Hash password and insert new user. Returns user id or None on failure."""
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s) RETURNING id;",
                    (name, email, hashed)
                )
                row = cur.fetchone()
                return row[0] if row else None
    except psycopg2.errors.UniqueViolation:
        print(f"[DB] Email already exists: {email}")
        return None
    except Exception as e:
        print(f"[DB] create_user error: {e}")
        return None


def get_user_by_email(email: str) -> dict | None:
    """Return user dict or None."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
                return cur.fetchone()
    except Exception as e:
        print(f"[DB] get_user_by_email error: {e}")
        return None


def get_user_by_id(user_id: int) -> dict | None:
    """Return user dict or None."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
                return cur.fetchone()
    except Exception as e:
        print(f"[DB] get_user_by_id error: {e}")
        return None


def verify_password(plain: str, hashed: str) -> bool:
    """Compare plain password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception as e:
        print(f"[DB] verify_password error: {e}")
        return False


# ── RESEARCH FUNCTIONS ────────────────────────────────────────────────────────

def save_research(results: dict, user_id: int) -> int | None:
    """Save a full analysis to the database. Returns the new row id."""
    try:
        idea = results.get("idea", "Unknown")
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO research (user_id, idea, results) VALUES (%s, %s, %s) RETURNING id;",
                    (user_id, idea, json.dumps(results))
                )
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        print(f"[DB] save_research error: {e}")
        return None


def get_history(user_id: int) -> list[dict]:
    """Return list of past research summaries for a user, newest first."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, idea, created_at,
                           results->'ai_insights'->>'verdict' AS verdict
                    FROM   research
                    WHERE  user_id = %s
                    ORDER  BY created_at DESC
                    LIMIT  50;
                """, (user_id,))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] get_history error: {e}")
        return []


def get_research_by_id(research_id: int) -> dict | None:
    """Return the full results dict for a single research row."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT results FROM research WHERE id = %s;",
                    (research_id,)
                )
                row = cur.fetchone()
                if row:
                    # results is already a dict when using JSONB + RealDictCursor
                    data = row["results"]
                    if isinstance(data, str):
                        data = json.loads(data)
                    return data
                return None
    except Exception as e:
        print(f"[DB] get_research_by_id error: {e}")
        return None


def delete_research(research_id: int) -> bool:
    """Delete a research row. Returns True on success."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM research WHERE id = %s;", (research_id,))
                return cur.rowcount > 0
    except Exception as e:
        print(f"[DB] delete_research error: {e}")
        return False
