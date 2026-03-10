# ============================================================
# DATABASE/DB.PY — PostgreSQL Version for Railway
# Uses SQLAlchemy for better PostgreSQL compatibility
# ============================================================

import os
import json
import bcrypt
from datetime import datetime
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool
from config import Config

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Fix for Railway's PostgreSQL URL (if it starts with postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine and session
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable pooling for simplicity
    echo=False
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ── 1. DEFINE MODELS ────────────────────────────────────────

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    researches = relationship("Research", back_populates="user")


class Research(Base):
    __tablename__ = 'research_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    idea = Column(String, nullable=False)
    ai_insights = Column(JSON, default={})
    market_data = Column(JSON, default={})
    competitors = Column(JSON, default=[])
    sales_forecast = Column(JSON, default={})
    niches = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="researches")
    reports = relationship("Report", back_populates="research")


class Report(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    research_id = Column(Integer, ForeignKey('research_history.id'))
    pdf_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    research = relationship("Research", back_populates="reports")


# ── 2. INITIALIZE DATABASE ──────────────────────────────────
def init_db(app):
    with app.app_context():
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✅ PostgreSQL database initialized successfully")


# ── 3. GET SESSION ──────────────────────────────────────────
def get_session():
    return SessionLocal()


# ── 4. USER FUNCTIONS ───────────────────────────────────────

def create_user(name, email, password):
    session = get_session()
    try:
        # Hash password
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")
        
        # Create user
        new_user = User(
            name=name,
            email=email,
            password=hashed
        )
        
        session.add(new_user)
        session.commit()
        
        user_id = new_user.id
        print(f"✅ User created: {email}")
        return user_id
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to create user: {e}")
        return None
    finally:
        session.close()


def get_user_by_email(email):
    session = get_session()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user:
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "password": user.password,
                "created_at": user.created_at
            }
        return None
    except Exception as e:
        print(f"❌ Failed to get user: {e}")
        return None
    finally:
        session.close()


def get_user_by_id(user_id):
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at
            }
        return None
    except Exception as e:
        print(f"❌ Failed to get user: {e}")
        return None
    finally:
        session.close()


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ── 5. SAVE RESEARCH ────────────────────────────────────────
def save_research(results, user_id=None):
    session = get_session()
    try:
        new_research = Research(
            user_id=user_id,
            idea=results["idea"],
            ai_insights=results.get("ai_insights", {}),
            market_data=results.get("market_data", {}),
            competitors=results.get("competitors", []),
            sales_forecast=results.get("sales_forecast", {}),
            niches=results.get("niches", [])
        )
        
        session.add(new_research)
        session.commit()
        
        research_id = new_research.id
        print(f"✅ Research saved with ID: {research_id}")
        return research_id
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to save research: {e}")
        return None
    finally:
        session.close()


# ── 6. GET HISTORY ──────────────────────────────────────────
def get_history(user_id=None):
    session = get_session()
    try:
        query = session.query(Research.id, Research.idea, Research.created_at)
        
        if user_id:
            query = query.filter(Research.user_id == user_id)
        
        results = query.order_by(Research.created_at.desc()).all()
        
        history = [
            {
                "id": r.id,
                "idea": r.idea,
                "created_at": r.created_at
            }
            for r in results
        ]
        
        print(f"📊 Retrieved {len(history)} history items")
        return history
        
    except Exception as e:
        print(f"❌ Failed to fetch history: {e}")
        return []
    finally:
        session.close()


# ── 7. GET RESEARCH BY ID ───────────────────────────────────
def get_research_by_id(research_id):
    session = get_session()
    try:
        research = session.query(Research).filter(Research.id == research_id).first()
        
        if research:
            return {
                "id": research.id,
                "idea": research.idea,
                "ai_insights": research.ai_insights or {},
                "market_data": research.market_data or {},
                "competitors": research.competitors or [],
                "sales_forecast": research.sales_forecast or {},
                "niches": research.niches or [],
                "created_at": research.created_at
            }
        return None
        
    except Exception as e:
        print(f"❌ Failed to fetch research: {e}")
        return None
    finally:
        session.close()


# ── 8. DELETE RESEARCH ──────────────────────────────────────
def delete_research(research_id):
    session = get_session()
    try:
        research = session.query(Research).filter(Research.id == research_id).first()
        if research:
            session.delete(research)
            session.commit()
            print(f"🗑️ Deleted research ID: {research_id}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to delete research: {e}")
    finally:
        session.close()


# ── 9. SAVE REPORT PATH ─────────────────────────────────────
def save_report(research_id, pdf_path):
    session = get_session()
    try:
        new_report = Report(
            research_id=research_id,
            pdf_path=pdf_path
        )
        
        session.add(new_report)
        session.commit()
        print(f"📄 Saved report path for research ID: {research_id}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to save report: {e}")
    finally:
        session.close()
