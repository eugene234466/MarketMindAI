# ============================================================
# DATABASE/DB.PY — SQLite
# ============================================================
import os
import json
import bcrypt
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "marketmind.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── INIT ──────────────────────────────────────────────────────

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT        NOT NULL,
                email      TEXT UNIQUE NOT NULL,
                password   TEXT        NOT NULL,
                created_at TEXT        NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS research (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                idea       TEXT    NOT NULL,
                results    TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_research_user_id ON research(user_id);

            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'pending',
                research_id INTEGER,
                error       TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        # Clean up stale jobs and expired tokens
        conn.execute("DELETE FROM jobs WHERE created_at < datetime('now', '-1 hour')")
        conn.execute("DELETE FROM password_reset_tokens WHERE expires_at < datetime('now')")
    print("[DB] SQLite ready.")


# ── JOB FUNCTIONS ─────────────────────────────────────────────

def create_job(job_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO jobs (id, status) VALUES (?, 'pending')",
            (job_id,)
        )

def complete_job(job_id: str, research_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status='done', research_id=? WHERE id=?",
            (research_id, job_id)
        )

def fail_job(job_id: str, error: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status='error', error=? WHERE id=?",
            (error[:500], job_id)
        )

def get_job(job_id: str) -> dict | None:
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"[DB] get_job error: {e}")
        return None

def delete_job(job_id: str):
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    except Exception:
        pass


# ── USER FUNCTIONS ─────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> int | None:
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed)
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    except Exception as e:
        print(f"[DB] create_user error: {e}")
        return None

def get_user_by_email(email: str) -> dict | None:
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"[DB] get_user_by_email error: {e}")
        return None

def get_user_by_id(user_id: int) -> dict | None:
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"[DB] get_user_by_id error: {e}")
        return None

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def increment_usage(user_id: int):
    pass  # Reserved for future analytics


# ── RESEARCH FUNCTIONS ─────────────────────────────────────────

def save_research(results: dict, user_id: int) -> int | None:
    try:
        idea = results.get("idea", "Unknown")
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO research (user_id, idea, results) VALUES (?, ?, ?)",
                (user_id, idea, json.dumps(results))
            )
            return cur.lastrowid
    except Exception as e:
        print(f"[DB] save_research error: {e}")
        return None

def get_history(user_id: int, limit: int = 50) -> list[dict]:
    try:
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT id, idea, created_at,
                       json_extract(results, '$.ai_insights.verdict') AS verdict
                FROM   research
                WHERE  user_id=?
                ORDER  BY created_at DESC
                LIMIT  ?
            """, (user_id, limit)).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] get_history error: {e}")
        return []

def get_research_by_id(research_id: int) -> dict | None:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT results FROM research WHERE id=?", (research_id,)
            ).fetchone()
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
            conn.execute("DELETE FROM research WHERE id=?", (research_id,))
            return True
    except Exception as e:
        print(f"[DB] delete_research error: {e}")
        return False


# ── PASSWORD RESET FUNCTIONS ───────────────────────────────────

def create_reset_token(user_id: int, token: str):
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (user_id,))
            conn.execute(
                "INSERT INTO password_reset_tokens (token, user_id, expires_at) "
                "VALUES (?, ?, datetime('now', '+1 hour'))",
                (token, user_id)
            )
    except Exception as e:
        print(f"[DB] create_reset_token error: {e}")

def get_reset_token(token: str) -> dict | None:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM password_reset_tokens "
                "WHERE token=? AND expires_at > datetime('now')",
                (token,)
            ).fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"[DB] get_reset_token error: {e}")
        return None

def delete_reset_token(token: str):
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM password_reset_tokens WHERE token=?", (token,))
    except Exception as e:
        print(f"[DB] delete_reset_token error: {e}")

def update_password(user_id: int, new_password: str) -> bool:
    try:
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        with get_conn() as conn:
            conn.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
        return True
    except Exception as e:
        print(f"[DB] update_password error: {e}")
        return False
