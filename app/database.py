"""
Database configuration and session management.
Uses SQLAlchemy with SQLite for local development.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Create engine with SQLite-specific settings
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
    poolclass=StaticPool,  # Use static pool for SQLite
    echo=settings.DEBUG
)

# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """Initialize database and create all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        
        # Initialize default configurations
        from .services.risk_engine import RiskEngineService
        db = SessionLocal()
        try:
            RiskEngineService.initialize_default_config(db)
            db.commit()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database session (for non-FastAPI use)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
