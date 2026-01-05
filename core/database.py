"""
Database connection and session management.
Separated from models for better organization.
Optimized for Neon PostgreSQL with proper connection pooling.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine with proper settings for SQLite vs PostgreSQL/Neon
if "sqlite" in settings.database_url:
    # SQLite settings
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
    )
    logger.info("Using SQLite database (local development)")
else:
    # PostgreSQL/Neon settings with connection pooling
    engine = create_engine(
        settings.database_url,
        pool_size=5,              # Number of connections to maintain
        max_overflow=10,          # Additional connections when needed
        pool_pre_ping=True,       # Validates connections before use
        pool_recycle=3600,        # Recycle connections after 1 hour (important for Neon)
        echo=False                # Set to True for SQL query logging
    )
    logger.info("Using PostgreSQL database (Neon or other)")

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Use with FastAPI Depends() to automatically handle session lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and warm up connection pool"""
    # Import models here to avoid circular imports
    from models.auction import AuctionItem
    Base.metadata.create_all(bind=engine)
    
    # Warm up connection pool to prevent cold start on first request
    if "postgresql" in settings.database_url.lower():
        logger.info("Warming up Neon connection pool...")
        import time
        start = time.time()
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            elapsed = time.time() - start
            logger.info(f"Connection pool warmed up in {elapsed:.3f}s")
            
            if elapsed > 3.0:
                logger.warning(f"⚠️ Neon cold start detected ({elapsed:.1f}s)")
                logger.warning("   This is normal for Neon free tier after inactivity")
                logger.warning("   Subsequent queries will be fast (~0.4s)")
        except Exception as e:
            logger.error(f"Connection warm-up failed: {e}")


def keep_alive():
    """Keep database connection alive to prevent Neon from sleeping"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        logger.debug("Database keep-alive ping successful")
        return True
    except Exception as e:
        logger.warning(f"Database keep-alive failed: {e}")
        return False
