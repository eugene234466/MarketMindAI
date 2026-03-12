# ============================================================
# DATABASE/DB.PY
# ============================================================
import sqlite3
import json
import hashlib
from datetime import datetime

DB_PATH = "database/database.db"


# ── CONNECTION ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_conn():
    return get_db()


# ── PASSWORD UTILS ──────────────────────────────────────────
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str):
    return hash_password(password) == hashed


# ── USER FUNCTIONS ──────────────────────────────────────────
def create_user(name, email, password):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO users (name, email, password, plan)
            VALUES (?, ?, ?, 'free')
            """,
            (name, email, hash_password(password)),
        )

        conn.commit()
        user_id = cur.lastrowid
        conn.close()

        return user_id

    except Exception as e:
        print("[DB create_user]", e)
        return None


def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()

    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()

    conn.close()
    return dict(row) if row else None


def get_user_by_stripe_customer(customer_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,))
    row = cur.fetchone()

    conn.close()
    return dict(row) if row else None


def update_user_plan(user_id, plan, stripe_customer_id=None, stripe_subscription_id=None):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET plan=?,
                stripe_customer_id = COALESCE(?, stripe_customer_id),
                stripe_subscription_id = COALESCE(?, stripe_subscription_id)
            WHERE id=?
            """,
            (plan, stripe_customer_id, stripe_subscription_id, user_id),
        )

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print("[DB update_user_plan]", e)
        return False


def cancel_user_plan(user_id):
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET plan='free',
                stripe_subscription_id=NULL
            WHERE id=?
            """,
            (user_id,),
        )

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print("[DB cancel_user_plan]", e)
        return False


# ── USAGE TRACKING ──────────────────────────────────────────
def get_user_usage(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) as count FROM research WHERE user_id=?",
        (user_id,),
    )

    row = cur.fetchone()
    conn.close()

    return row["count"] if row else 0


def increment_usage(user_id):
    # usage already tracked by research table
    return True


# ── RESEARCH STORAGE ────────────────────────────────────────
def save_research(results, user_id):
    try:
        conn = get_db()
        cur = conn.cursor()

        idea = results.get("idea") if isinstance(results, dict) else None

        cur.execute(
            """
            INSERT INTO research (user_id, idea, results, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                idea,
                json.dumps(results),
                datetime.utcnow().isoformat(),
            ),
        )

        conn.commit()
        research_id = cur.lastrowid
        conn.close()

        return research_id

    except Exception as e:
        print("[DB save_research]", e)
        return None


def get_history(user_id, limit=50):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, idea, created_at
        FROM research
        WHERE user_id=?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )

    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_research_by_id(research_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM research WHERE id=?",
        (research_id,),
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    r = dict(row)
    r["results"] = json.loads(r["results"])
    return r["results"]


def delete_research(research_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM research WHERE id=?", (research_id,))

    conn.commit()
    conn.close()


# ── BACKGROUND JOB SYSTEM ───────────────────────────────────
def create_job(job_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO jobs (id, status) VALUES (?, 'pending')",
        (job_id,),
    )

    conn.commit()
    conn.close()


def complete_job(job_id, research_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status='done', research_id=?
        WHERE id=?
        """,
        (research_id, job_id),
    )

    conn.commit()
    conn.close()


def fail_job(job_id, error):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status='error', error=?
        WHERE id=?
        """,
        (error, job_id),
    )

    conn.commit()
    conn.close()


def get_job(job_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    row = cur.fetchone()

    conn.close()

    return dict(row) if row else None


def delete_job(job_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM jobs WHERE id=?", (job_id,))

    conn.commit()
    conn.close()
