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

def init_db(app=None):
    """Create tables if they don't exist. Call once at app startup.
    The app parameter is accepted for compatibility but not used."""
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
                user_id = row[0] if row else None
                print(f"[DB] User created: {email} with ID: {user_id}")
                return user_id
    except psycopg2.errors.UniqueViolation:
        print(f"[DB] Email already exists: {email}")
        return None
    except Exception as e:
        print(f"[DB] create_user error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_user_by_email(email: str) -> dict | None:
    """Return user dict or None."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        print(f"[DB] get_user_by_email error: {e}")
        return None


def get_user_by_id(user_id: int) -> dict | None:
    """Return user dict or None."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None
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

def save_research(results: dict, user_id: int = None) -> int | None:
    """Save a full analysis to the database. Returns the new row id."""
    try:
        if not results:
            print("[DB] No results to save")
            return None
            
        idea = results.get("idea", "Unknown")
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO research (user_id, idea, results) VALUES (%s, %s, %s) RETURNING id;",
                    (user_id, idea, json.dumps(results))
                )
                row = cur.fetchone()
                research_id = row[0] if row else None
                print(f"[DB] Research saved with ID: {research_id} for idea: {idea}")
                return research_id
    except Exception as e:
        print(f"[DB] save_research error: {e}")
        import traceback
        traceback.print_exc()
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
                history = []
                for r in rows:
                    history.append({
                        "id": r["id"],
                        "idea": r["idea"],
                        "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else None,
                        "verdict": r.get("verdict", "N/A")
                    })
                print(f"[DB] Retrieved {len(history)} history items for user {user_id}")
                return history
    except Exception as e:
        print(f"[DB] get_history error: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_research_by_id(research_id: int) -> dict | None:
    """Return the full results dict for a single research row."""
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM research WHERE id = %s;",
                    (research_id,)
                )
                row = cur.fetchone()
                if row:
                    # Convert row to dict
                    result = dict(row)
                    
                    # Parse results JSON if needed
                    if 'results' in result:
                        if isinstance(result['results'], str):
                            results_data = json.loads(result['results'])
                        else:
                            results_data = result['results']
                    else:
                        results_data = {}
                    
                    # Add metadata
                    results_data['id'] = result['id']
                    results_data['user_id'] = result['user_id']
                    if result.get('created_at'):
                        results_data['created_at'] = result['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                    
                    print(f"[DB] Retrieved research ID {research_id}")
                    return results_data
                return None
    except Exception as e:
        print(f"[DB] get_research_by_id error: {e}")
        import traceback
        traceback.print_exc()
        return None


def delete_research(research_id: int) -> bool:
    """Delete a research row. Returns True on success."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM research WHERE id = %s;", (research_id,))
                deleted = cur.rowcount > 0
                if deleted:
                    print(f"[DB] Deleted research ID: {research_id}")
                return deleted
    except Exception as e:
        print(f"[DB] delete_research error: {e}")
        return False
