# ============================================================
# DATABASE/DB.PY — FULL UPDATED VERSION
# Added users table + auth functions
# Fixed persistence with Railway volumes
# ============================================================

import sqlite3
import json
import bcrypt
import os
from datetime import datetime
from config import Config


# ── 1. INITIALIZE DATABASE ──────────────────────────────────
def init_db(app):
    with app.app_context():
        # Ensure database directory exists
        db_dir = os.path.dirname(Config.DATABASE_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"📁 Created database directory: {db_dir}")
        
        conn   = get_connection()
        cursor = conn.cursor()

        # ── EXISTING TABLES ──────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER,
                idea            TEXT NOT NULL,
                ai_insights     TEXT,
                market_data     TEXT,
                competitors     TEXT,
                sales_forecast  TEXT,
                niches          TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                research_id     INTEGER,
                pdf_path        TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (research_id) REFERENCES research_history(id)
            )
        """)

        # ── NEW USERS TABLE ───────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                email           TEXT UNIQUE NOT NULL,
                password        TEXT NOT NULL,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        print(f"✅ Database initialized successfully at {Config.DATABASE_PATH}")


# ── 2. GET CONNECTION ────────────────────────────────────────
def get_connection():
    # Create database directory if it doesn't exist (safety check)
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 3. USER FUNCTIONS ────────────────────────────────────────

def create_user(name, email, password):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # ── HASH PASSWORD ────────────────────────────────────
        # Never store plain text passwords
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute("""
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
        """, (name, email, hashed))

        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        print(f"✅ User created: {email}")
        return user_id

    except sqlite3.IntegrityError:
        # Email already exists
        print(f"⚠️ Email already exists: {email}")
        return None

    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        return None


def get_user_by_email(email):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users WHERE email = ?
        """, (email,))

        row  = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id"        : row["id"],
                "name"      : row["name"],
                "email"     : row["email"],
                "password"  : row["password"],
                "created_at": row["created_at"]
            }
        return None

    except Exception as e:
        print(f"❌ Failed to get user: {e}")
        return None


def get_user_by_id(user_id):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users WHERE id = ?
        """, (user_id,))

        row  = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id"        : row["id"],
                "name"      : row["name"],
                "email"     : row["email"],
                "created_at": row["created_at"]
            }
        return None

    except Exception as e:
        print(f"❌ Failed to get user: {e}")
        return None


def verify_password(plain_password, hashed_password):
    # Checks if plain password matches the stored hash
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ── 4. SAVE RESEARCH ─────────────────────────────────────────
def save_research(results, user_id=None):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_history
            (user_id, idea, ai_insights, market_data,
             competitors, sales_forecast, niches)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            results["idea"],
            json.dumps(results.get("ai_insights",    {})),
            json.dumps(results.get("market_data",    {})),
            json.dumps(results.get("competitors",    [])),
            json.dumps(results.get("sales_forecast", {})),
            json.dumps(results.get("niches",         []))
        ))

        conn.commit()
        research_id = cursor.lastrowid
        conn.close()
        print(f"✅ Research saved with ID: {research_id}")
        return research_id

    except Exception as e:
        print(f"❌ Failed to save research: {e}")
        return None


# ── 5. GET HISTORY ───────────────────────────────────────────
def get_history(user_id=None):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # ── FILTER BY USER IF LOGGED IN ──────────────────────
        if user_id:
            cursor.execute("""
                SELECT id, idea, created_at
                FROM research_history
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT id, idea, created_at
                FROM research_history
                ORDER BY created_at DESC
            """)

        rows    = cursor.fetchall()
        history = [
            {
                "id"        : row["id"],
                "idea"      : row["idea"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]

        conn.close()
        print(f"📊 Retrieved {len(history)} history items")
        return history

    except Exception as e:
        print(f"❌ Failed to fetch history: {e}")
        return []


# ── 6. GET RESEARCH BY ID ────────────────────────────────────
def get_research_by_id(research_id):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM research_history WHERE id = ?
        """, (research_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id"            : row["id"],
                "idea"          : row["idea"],
                "ai_insights"   : json.loads(row["ai_insights"]    or "{}"),
                "market_data"   : json.loads(row["market_data"]    or "{}"),
                "competitors"   : json.loads(row["competitors"]    or "[]"),
                "sales_forecast": json.loads(row["sales_forecast"] or "{}"),
                "niches"        : json.loads(row["niches"]         or "[]"),
                "created_at"    : row["created_at"]
            }
        return None

    except Exception as e:
        print(f"❌ Failed to fetch research: {e}")
        return None


# ── 7. DELETE RESEARCH ───────────────────────────────────────
def delete_research(research_id):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM research_history WHERE id = ?
        """, (research_id,))

        conn.commit()
        conn.close()
        print(f"🗑️ Deleted research ID: {research_id}")

    except Exception as e:
        print(f"❌ Failed to delete research: {e}")


# ── 8. SAVE REPORT PATH ──────────────────────────────────────
def save_report(research_id, pdf_path):
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO reports (research_id, pdf_path)
            VALUES (?, ?)
        """, (research_id, pdf_path))

        conn.commit()
        conn.close()
        print(f"📄 Saved report path for research ID: {research_id}")

    except Exception as e:
        print(f"❌ Failed to save report: {e}")
