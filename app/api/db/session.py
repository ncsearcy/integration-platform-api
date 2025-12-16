from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.api.core.config import settings
from app.api.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Create database engine
engine = create_engine(
    settings.database_url_sync,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,  # Verify connections before using them
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.

    Yields a database session and ensures it's closed after use.
    Use this as a FastAPI dependency.

    Example:
        @app.get("/clients")
        def get_clients(db: Session = Depends(get_db)):
            return db.query(Client).all()

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database.

    Creates all tables defined in the models.
    Should be called on application startup.
    """
    logger.info("initializing_database", database_url=settings.database_url_sync)

    try:
        # Import all models to ensure they're registered with Base
        from app.api.models import client, integration  # noqa: F401

        # Create all tables
        Base.metadata.create_all(bind=engine)

        logger.info("database_initialized", tables=list(Base.metadata.tables.keys()))
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e), exc_info=True)
        raise


def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data!
    Should only be used in development/testing.
    """
    if settings.is_production:
        logger.error("drop_db_blocked_in_production")
        raise RuntimeError("Cannot drop database in production environment")

    logger.warning("dropping_database", database_url=settings.database_url_sync)

    try:
        from app.api.models import client, integration  # noqa: F401

        Base.metadata.drop_all(bind=engine)
        logger.warning("database_dropped")
    except Exception as e:
        logger.error("database_drop_failed", error=str(e), exc_info=True)
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        from sqlalchemy import text

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("database_connection_check_success")
        return True
    except Exception as e:
        logger.error("database_connection_check_failed", error=str(e))
        return False
