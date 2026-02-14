"""
Database connection for Vercel Postgres (Neon).

Key difference from local: Uses NullPool since serverless functions
don't maintain persistent connection pools between invocations.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from config import get_config

Base = declarative_base()

# Cache engine per process (Vercel may reuse the process for warm starts)
_engine = None


def get_engine():
    """Get or create SQLAlchemy engine with NullPool for serverless."""
    global _engine
    if _engine is None:
        config = get_config()
        if not config.DATABASE_URL:
            raise RuntimeError("POSTGRES_URL not set. Connect Postgres via Vercel Storage tab.")
        _engine = create_engine(
            config.DATABASE_URL,
            poolclass=NullPool,  # No connection pooling in serverless
            echo=False,
        )
    return _engine


def get_session():
    """Create a new database session. Caller must close it."""
    engine = get_engine()
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


def init_db():
    """Create all tables. Call once via /api/setup-db."""
    # Import models so Base knows about them
    import models.call_log
    import models.caller_history
    import models.menu_config
    Base.metadata.create_all(bind=get_engine())
