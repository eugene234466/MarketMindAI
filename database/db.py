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

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_pool = None


def get_pool():
    global _pool

    if _pool is None:

        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set")

        _pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL
        )

        print("[DB] Connection pool created.")

    return _pool


@contextmanager
def get_conn():

    pool = get_pool()
    conn = pool.getconn()

    try:

        # check connection health
        if conn.closed != 0:
            conn = psycopg2.connect(DATABASE_URL)

        with conn.cursor() as cur:
            cur.execute("SELECT 1")

        yield conn
        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        if conn.closed == 0:
            pool.putconn(conn)
        else:
            conn.close()


# ─────────────────────────────────────────────
# INIT TABLES
# ─────────────────────────────────────────────

def init_db():

    with get_conn() as conn:
        with conn.cursor() as cur:

            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS research (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                idea TEXT NOT NULL,
                results JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_user_id
            ON research(user_id);
            """)

    print("[DB] Tables ready.")


# ─────────────────────────────────────────────
# USER FUNCTIONS
# ─────────────────────────────────────────────

def create_user(name, email, password):

    try:

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        with get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    "INSERT INTO users (name,email,password) VALUES (%s,%s,%s) RETURNING id;",
                    (name, email.lower(), hashed)
                )

                row = cur.fetchone()
                return row[0] if row else None

    except psycopg2.errors.UniqueViolation:

        print(f"[DB] Email exists: {email}")
        return None

    except Exception as e:

        print(f"[DB] create_user error: {e}")
        return None


def get_user_by_email(email):

    try:

        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                cur.execute(
                    "SELECT * FROM users WHERE LOWER(email)=LOWER(%s);",
                    (email,)
                )

                return cur.fetchone()

    except Exception as e:

        print(f"[DB] get_user_by_email error: {e}")
        return None


def get_user_by_id(user_id):

    try:

        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                cur.execute(
                    "SELECT * FROM users WHERE id=%s;",
                    (user_id,)
                )

                return cur.fetchone()

    except Exception as e:

        print(f"[DB] get_user_by_id error: {e}")
        return None


def verify_password(plain, hashed):

    try:

        return bcrypt.checkpw(
            plain.encode(),
            hashed.encode()
        )

    except Exception as e:

        print(f"[DB] verify_password error: {e}")
        return False


# ─────────────────────────────────────────────
# RESEARCH FUNCTIONS
# ─────────────────────────────────────────────

def save_research(results, user_id):

    try:

        idea = results.get("idea", "Unknown")

        with get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    "INSERT INTO research (user_id,idea,results) VALUES (%s,%s,%s) RETURNING id;",
                    (user_id, idea, psycopg2.extras.Json(results))
                )

                row = cur.fetchone()
                return row[0] if row else None

    except Exception as e:

        print(f"[DB] save_research error: {e}")
        return None


def get_history(user_id):

    try:

        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                cur.execute("""
                SELECT id,idea,created_at,
                       results->>'verdict' AS verdict
                FROM research
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT 50
                """, (user_id,))

                return [dict(r) for r in cur.fetchall()]

    except Exception as e:

        print(f"[DB] get_history error: {e}")
        return []


def get_research_by_id(research_id):

    try:

        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                cur.execute(
                    "SELECT results FROM research WHERE id=%s;",
                    (research_id,)
                )

                row = cur.fetchone()

                if row:

                    data = row["results"]

                    if isinstance(data, str):
                        data = json.loads(data)

                    return data

                return None

    except Exception as e:

        print(f"[DB] get_research_by_id error: {e}")
        return None


def delete_research(research_id):

    try:

        with get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    "DELETE FROM research WHERE id=%s;",
                    (research_id,)
                )

                return cur.rowcount > 0

    except Exception as e:

        print(f"[DB] delete_research error: {e}")
        return False
