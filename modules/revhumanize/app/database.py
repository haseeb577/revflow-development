import os
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rr_automation:ebx9CMvWRHuAt8AfbuQECT3e@172.17.0.1:5432/api_engine_db"
)

# Try to connect but don't fail if unavailable
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 2})
    with engine.connect() as conn:
        pass
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    DB_AVAILABLE = True
    print("✅ Database connected")
except Exception as e:
    print(f"⚠️  DB unavailable (continuing): {e}")
    engine = None
    SessionLocal = None
    DB_AVAILABLE = False

Base = declarative_base()

def init_db():
    """Initialize database tables"""
    if DB_AVAILABLE and engine:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized")
    else:
        print("⚠️  Skipping DB init (database unavailable)")

@contextmanager
def get_db() -> Generator[Optional[Session], None, None]:
    """Get database session context manager"""
    if not DB_AVAILABLE or SessionLocal is None:
        yield None
        return
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Optional[Session]:
    """Get database session (non-context manager)"""
    if not DB_AVAILABLE or SessionLocal is None:
        return None
    return SessionLocal()
