"""
Database configuration module for phoGPT training service.
Provides PostgreSQL connection management with connection pooling and session handling.
"""

import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DbConfig:
    """
    Database configuration and connection management for phoGPT training service.
    Handles PostgreSQL connections with connection pooling and session management.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize database configuration.

        Args:
            host: Database host (default from env or 'localhost')
            port: Database port (default from env or 5432)
            database: Database name (default from env or 'phogpt_db')
            username: Database username (default from env or 'postgres')
            password: Database password (default from env or 'postgres')
        """
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or int(os.getenv("DB_PORT", "5432"))
        self.database = database or os.getenv("DB_NAME", "phogpt_db")
        self.username = username or os.getenv("DB_USER", "postgres")
        self.password = password or os.getenv("DB_PASSWORD", "postgres")

        # Connection pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))

        # Engine and session
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None

        # Initialize connection
        self._initialize_engine()

    @property
    def database_url(self) -> str:
        """
        Construct PostgreSQL database URL.

        Returns:
            Database connection URL
        """
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with connection pooling."""
        try:
            logger.info(f"Initializing database connection to {self.host}:{self.port}/{self.database}")

            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,  # Verify connections before use
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                connect_args={"options": "-c timezone=utc"},
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,  # Keep attributes accessible after commit
                bind=self.engine,
            )

            logger.info("Database engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            raise

    def validate_config(self) -> bool:
        """
        Validate database configuration.

        Returns:
            True if configuration is valid
        """
        required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.warning(f"Missing database environment variables: {missing_vars}")
            logger.info("Using default values for missing configuration")

        return True

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection is successful, False otherwise
        """
        if self.engine is None:
            logger.error("Database engine not initialized")
            return False

        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session with automatic cleanup and transaction management.

        Yields:
            Database session

        Example:
            with db_config.get_session() as session:
                result = session.execute(text("SELECT * FROM table"))
        """
        if self.SessionLocal is None:
            raise RuntimeError("Database session maker not initialized")

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    def get_session_dependency(self):
        """
        FastAPI dependency for database sessions.

        Yields:
            Database session
        """
        with self.get_session() as session:
            yield session

    def create_tables(self, base) -> None:
        """
        Create all tables defined in the Base metadata.

        Args:
            base: SQLAlchemy declarative base
        """
        try:
            base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise

    def drop_tables(self, base) -> None:
        """
        Drop all tables defined in the Base metadata.

        Args:
            base: SQLAlchemy declarative base
        """
        try:
            base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop database tables: {str(e)}")
            raise

    def execute_raw_sql(self, sql: str, params: Optional[dict] = None):
        """
        Execute raw SQL query.

        Args:
            sql: SQL query string
            params: Optional query parameters

        Returns:
            Query result
        """
        if self.engine is None:
            raise RuntimeError("Database engine not initialized")

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql), params or {})
                connection.commit()
                return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to execute raw SQL: {str(e)}")
            raise

    def get_engine_info(self) -> dict:
        """
        Get information about the database engine and connection pool.

        Returns:
            Dictionary containing engine information
        """
        if self.engine is None:
            return {"status": "not_initialized"}

        pool = self.engine.pool
        info = {
            "database_url": f"postgresql://{self.host}:{self.port}/{self.database}",
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
        }

        # Try to get pool status (may not be available for all pool types)
        try:
            if hasattr(pool, "size"):
                info["current_pool_size"] = pool.size()  # type: ignore
            else:
                info["current_pool_size"] = "N/A"

            if hasattr(pool, "checkedout"):
                info["checked_out_connections"] = pool.checkedout()  # type: ignore
            else:
                info["checked_out_connections"] = "N/A"
        except Exception:
            info["current_pool_size"] = "N/A"
            info["checked_out_connections"] = "N/A"

        return info

    def print_config_info(self) -> None:
        """Print database configuration information."""
        print("=" * 80)
        print("DATABASE CONFIGURATION")
        print("=" * 80)
        print(f"\nHost: {self.host}")
        print(f"Port: {self.port}")
        print(f"Database: {self.database}")
        print(f"Username: {self.username}")
        print(f"\nConnection Pool Settings:")
        print(f"  Pool Size: {self.pool_size}")
        print(f"  Max Overflow: {self.max_overflow}")
        print(f"  Pool Timeout: {self.pool_timeout}s")
        print(f"  Pool Recycle: {self.pool_recycle}s")

        if self.engine:
            info = self.get_engine_info()
            print(f"\nCurrent Pool Status:")
            print(f"  Current Size: {info.get('current_pool_size', 'N/A')}")
            print(f"  Checked Out: {info.get('checked_out_connections', 'N/A')}")

        print("\n" + "=" * 80)

    def close(self) -> None:
        """Close database engine and cleanup resources."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine closed")


# Global database configuration instance
_db_config: Optional[DbConfig] = None


def get_db_config() -> DbConfig:
    """
    Get global database configuration instance (singleton pattern).

    Returns:
        DbConfig instance
    """
    global _db_config
    if _db_config is None:
        _db_config = DbConfig()
    return _db_config


def initialize_db_config(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> DbConfig:
    """
    Initialize global database configuration.

    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password

    Returns:
        Initialized DbConfig instance
    """
    global _db_config
    _db_config = DbConfig(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
    )
    return _db_config


def close_db_config() -> None:
    """Close global database configuration."""
    global _db_config
    if _db_config:
        _db_config.close()
        _db_config = None


def test_database_setup() -> bool:
    """
    Test database setup and configuration.

    Returns:
        True if all tests pass, False otherwise
    """
    try:
        db = get_db_config()

        # Validate configuration
        if not db.validate_config():
            logger.error("✗ Database configuration validation failed")
            return False

        # Test connection
        if db.test_connection():
            logger.info("✓ Database connection successful")
        else:
            logger.error("✗ Database connection failed")
            return False

        # Test session creation
        with db.get_session() as session:
            result = session.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✓ PostgreSQL version: {version}")

        # Print configuration info
        db.print_config_info()

        return True

    except Exception as e:
        logger.error(f"✗ Database setup test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run database connection test
    test_database_setup()