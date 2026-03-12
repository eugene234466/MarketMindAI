# ============================================================
# DATABASE/DB.PY — PostgreSQL with Connection Pooling
# ============================================================
import os
import json
import bcrypt
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_pool: ThreadedConnectionPool = None


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set.")
        _pool = ThreadedConnectionPool(
            minconn=1, maxconn=5, dsn=DATABASE_URL,
            keepalives=1, keepalives_idle=10,
            keepalives_interval=5, keepalives_count=3
        )
        print("[DB] Connection pool created.")
    return _pool


def _is_conn_alive(conn) -> bool:
    try:
        conn.cursor().execute("SELECT 1")
        return True
    except Exception:
        return False


def _reset_pool():
    global _pool
    try:
        if _pool: _pool.closeall()
    except Exception:
        pass
    _pool = None
    print("[DB] Pool reset — will reconnect on next request")


@contextmanager
def get_conn():
    for attempt in range(2):
        pool = get_pool()
        conn = pool.getconn()

        # Discard stale connections immediately rather than failing mid-query
        if not _is_conn_alive(conn):
            try: pool.putconn(conn, close=True)
            except Exception: pass
            _reset_pool()
            if attempt == 1:
                raise psycopg2.OperationalError("Could not obtain a live DB connection after retry")
            continue

        try:
            yield conn
            conn.commit()
            pool.putconn(conn)
            return
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            try: pool.putconn(conn, close=True)
            except Exception: pass
            _reset_pool()
            if attempt == 1:
                raise
        except Exception:
            try: conn.rollback()
            except Exception: pass
            try: pool.putconn(conn)
            except Exception: pass
            raise


# ── INIT ──────────────────────────────────────────────────────

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:

            # Users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    name       TEXT        NOT NULL,
                    email      TEXT UNIQUE NOT NULL,
                    password   TEXT        NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            # Research
            cur.execute("""
                CREATE TABLE IF NOT EXISTS research (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    idea       TEXT        NOT NULL,
                    results    JSONB       NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_research_user_id ON research(user_id);")

            # Jobs (background pipeline tracking)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          TEXT PRIMARY KEY,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    research_id INTEGER,
                    error       TEXT,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("DELETE FROM jobs WHERE created_at < NOW() - INTERVAL '1 hour';")

    print("[DB] Tables ready.")


# ── JOB FUNCTIONS ─────────────────────────────────────────────

def create_job(job_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (id, status) VALUES (%s, 'pending') ON CONFLICT (id) DO NOTHING;",
                (job_id,)
            )

def complete_job(job_id: str, research_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET status='done', research_id=%s WHERE id=%s;", (research_id, job_id))

def fail_job(job_id: str, error: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET status='error', error=%s WHERE id=%s;", (error[:500], job_id))

def get_job(job_id: str) -> dict | None:
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE id=%s;", (job_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        print(f"[DB] get_job error: {e}")
        return None

def delete_job(job_id: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM jobs WHERE id=%s;", (job_id,))
    except Exception:
        pass


# ── USER FUNCTIONS ─────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> int | None:
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
        return None
    except Exception as e:
        print(f"[DB] create_user error: {e}")
        return None

def get_user_by_email(email: str) -> dict | None:
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE email=%s;", (email,))
                return cur.fetchone()
    except Exception as e:
        print(f"[DB] get_user_by_email error: {e}")
        return None

def get_user_by_id(user_id: int) -> dict | None:
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id=%s;", (user_id,))
                return cur.fetchone()
    except Exception as e:
        print(f"[DB] get_user_by_id error: {e}")
        return None

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def increment_usage(user_id: int):
    # Kept as a no-op for now — can wire up analytics later
    pass


# ── RESEARCH FUNCTIONS ─────────────────────────────────────────

def save_research(results: dict, user_id: int) -> int | None:
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

def get_history(user_id: int, limit: int = 50) -> list[dict]:
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, idea, created_at,
                           results->'ai_insights'->>'verdict' AS verdict
                    FROM   research
                    WHERE  user_id=%s
                    ORDER  BY created_at DESC
                    LIMIT  %s;
                """, (user_id, limit))
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB] get_history error: {e}")
        return []

def get_research_by_id(research_id: int) -> dict | None:
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT results FROM research WHERE id=%s;", (research_id,))
                row = cur.fetchone()
                if row:
                    data = row["results"]
                    return data if isinstance(data, dict) else json.loads(data)
                return None
    except Exception as e:
        print(f"[DB] get_research_by_id error: {e}")
        return None

def delete_research(research_id: int) -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM research WHERE id=%s;", (research_id,))
                return cur.rowcount > 0
    except Exception as e:
        print(f"[DB] delete_research error: {e}")
        return False
