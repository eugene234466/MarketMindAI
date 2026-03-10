# ============================================================
# DATABASE/DB.PY — PostgreSQL Version for Railway
# COMPLETE - NO ERRORS
# ============================================================

import os
import json
import bcrypt
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON
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
    poolclass=NullPool,
    echo=False
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ── 1. DEFINE MODELS ────────────────────────────────────────

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, default="User")
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    researches = relationship("Research", back_populates="user", cascade="all, delete-orphan")


class Research(Base):
    __tablename__ = 'research_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    idea = Column(String, nullable=False, default="Untitled")
    ai_insights = Column(JSON, default={})
    market_data = Column(JSON, default={})
    competitors = Column(JSON, default=[])
    sales_forecast = Column(JSON, default={})
    niches = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="researches")
    reports = relationship("Report", back_populates="research", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    research_id = Column(Integer, ForeignKey('research_history.id', ondelete='CASCADE'))
    pdf_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    research = relationship("Research", back_populates="reports")


# ── 2. INITIALIZE DATABASE ──────────────────────────────────
def init_db(app):
    with app.app_context():
        Base.metadata.create_all(bind=engine)
        print("✅ PostgreSQL database initialized successfully")


# ── 3. GET SESSION ──────────────────────────────────────────
def get_session():
    return SessionLocal()


# ── 4. USER FUNCTIONS ───────────────────────────────────────

def create_user(name, email, password):
    session = get_session()
    try:
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")
        
        new_user = User(
            name=name or "User",
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
                "name": user.name or "User",
                "email": user.email,
                "password": user.password,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None
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
        if not user_id:
            return None
            
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            return {
                "id": user.id,
                "name": user.name or "User",
                "email": user.email or "",
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None
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
            idea=results.get("idea", "Untitled"),
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
        query = session.query(
            Research.id, 
            Research.idea, 
            Research.created_at,
            Research.user_id
        )
        
        if user_id:
            query = query.filter(Research.user_id == user_id)
        else:
            return []
        
        query = query.order_by(Research.created_at.desc())
        results = query.all()
        
        history = []
        for r in results:
            created_at_str = None
            if r.created_at:
                try:
                    created_at_str = r.created_at.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    created_at_str = str(r.created_at)
            
            history.append({
                "id": r.id,
                "idea": r.idea or "Untitled",
                "created_at": created_at_str,
                "user_id": r.user_id
            })
        
        print(f"📊 Retrieved {len(history)} history items for user {user_id}")
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
        if not research_id:
            print(f"❌ get_research_by_id called with None research_id")
            return None
            
        research = session.query(Research).filter(Research.id == research_id).first()
        
        if research:
            # Safely parse JSON fields
            try:
                ai_insights = research.ai_insights or {}
            except:
                ai_insights = {}
                
            try:
                market_data = research.market_data or {}
            except:
                market_data = {}
                
            try:
                competitors = research.competitors or []
            except:
                competitors = []
                
            try:
                sales_forecast = research.sales_forecast or {}
            except:
                sales_forecast = {}
                
            try:
                niches = research.niches or []
            except:
                niches = []
            
            result = {
                "id": research.id,
                "user_id": research.user_id,
                "idea": research.idea or "Untitled",
                "ai_insights": ai_insights,
                "market_data": market_data,
                "competitors": competitors,
                "sales_forecast": sales_forecast,
                "niches": niches,
                "created_at": research.created_at.strftime("%Y-%m-%d %H:%M:%S") if research.created_at else None
            }
            print(f"✅ Retrieved research ID {research_id}")
            return result
        
        print(f"⚠️ Research ID {research_id} not found")
        return None
        
    except Exception as e:
        print(f"❌ Failed to fetch research {research_id}: {e}")
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
            return True
        else:
            print(f"⚠️ Research ID {research_id} not found")
            return False
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to delete research: {e}")
        return False
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
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to save report: {e}")
        return False
    finally:
        session.close()
