# ============================================================
# DATABASE/DB.PY — PostgreSQL with Connection Pooling
# FIXED: SSL connection issues, keepalives, retry logic
# ============================================================

import os
import json
import bcrypt
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import time

# ── CONNECTION POOL ──────────────────────────────────────────────────────────
# Railway injects DATABASE_URL automatically when you add a Postgres plugin.
# Min 1 connection, max 10 (safe for free/starter Railway plan).

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Railway sometimes provides postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Add SSL parameters to the connection string
if "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

_pool: ThreadedConnectionPool = None


def ensure_connection():
    """Test and reset pool if needed"""
    global _pool
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"[DB] Connection test failed: {e}")
        # Reset pool
        if _pool:
            try:
                _pool.closeall()
            except:
                pass
            _pool = None
        return False


def get_pool() -> ThreadedConnectionPool:
    """Lazily create the connection pool on first use."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Add a PostgreSQL plugin in Railway and it will be injected automatically."
            )
        _pool = ThreadedConnectionPool(
            minconn=1, 
            maxconn=10, 
            dsn=DATABASE_URL,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        print("[DB] Connection pool created.")
    return _pool


@contextmanager
def get_conn():
    """Context manager — borrows a connection from the pool and returns it."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        # Test the connection
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise
    finally:
        if conn:
            try:
                pool.putconn(conn)
            except:
                # If putconn fails, close and discard
                try:
                    conn.close()
                except:
                    pass


# ── INIT TABLES ──────────────────────────────────────────────────────────────

def init_db(app=None):
    """Create tables if they don't exist. Call once at app startup.
    The app parameter is accepted for compatibility but not used."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
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
            return
        except Exception as e:
            print(f"[DB] init_db attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                print("[DB] Failed to initialize tables after all retries")
                raise


# ── USER FUNCTIONS ────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> int | None:
    """Hash password and insert new user. Returns user id or None on failure."""
    max_retries = 3
    for attempt in range(max_retries):
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
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection error in create_user (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                ensure_connection()
                time.sleep(1)
                continue
            return None
        except Exception as e:
            print(f"[DB] create_user error: {e}")
            import traceback
            traceback.print_exc()
            return None


def get_user_by_email(email: str) -> dict | None:
    """Return user dict or None."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
                    row = cur.fetchone()
                    if row:
                        return dict(row)
                    return None
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection error in get_user_by_email (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                ensure_connection()
                time.sleep(1)
                continue
            return None
        except Exception as e:
            print(f"[DB] get_user_by_email error: {e}")
            return None


def get_user_by_id(user_id: int) -> dict | None:
    """Return user dict or None."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
                    row = cur.fetchone()
                    if row:
                        return dict(row)
                    return None
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection error in get_user_by_id (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                ensure_connection()
                time.sleep(1)
                continue
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
    """Save a full analysis to the database with retry logic."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
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
                    
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection error in save_research (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # Force pool to recreate connections
                global _pool
                if _pool:
                    try:
                        _pool.closeall()
                    except:
                        pass
                    _pool = None
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                print(f"[DB] save_research failed after {max_retries} attempts")
                import traceback
                traceback.print_exc()
                return None
                
        except Exception as e:
            print(f"[DB] save_research error: {e}")
            import traceback
            traceback.print_exc()
            return None


def get_history(user_id: int) -> list[dict]:
    """Return list of past research summaries for a user, newest first."""
    max_retries = 3
    for attempt in range(max_retries):
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
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection error in get_history (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                ensure_connection()
                time.sleep(1)
                continue
            return []
        except Exception as e:
            print(f"[DB] get_history error: {e}")
            import traceback
            traceback.print_exc()
            return []


def get_research_by_id(research_id: int) -> dict | None:
    """Return the full results dict for a single research row."""
    max_retries = 3
    for attempt in range(max_retries):
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
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection error in get_research_by_id (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                ensure_connection()
                time.sleep(1)
                continue
            return None
        except Exception as e:
            print(f"[DB] get_research_by_id error: {e}")
            import traceback
            traceback.print_exc()
            return None


def delete_research(research_id: int) -> bool:
    """Delete a research row. Returns True on success."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM research WHERE id = %s;", (research_id,))
                    deleted = cur.rowcount > 0
                    if deleted:
                        print(f"[DB] Deleted research ID: {research_id}")
                    return deleted
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection error in delete_research (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                ensure_connection()
                time.sleep(1)
                continue
            return False
        except Exception as e:
            print(f"[DB] delete_research error: {e}")
            return False
