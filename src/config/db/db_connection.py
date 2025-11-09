"""
Database connection module for PostgreSQL integration.
Provides connection pooling, session management, and database utilities.
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
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration management."""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.database = os.getenv('DB_NAME', 'chatbot_db')
        self.username = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'postgres')
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '50'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '100'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '60'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def validate_config(self) -> bool:
        """Validate database configuration."""
        required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing database environment variables: {missing_vars}")
            logger.info("Using default values for missing configuration")
        
        return True


class DatabaseConnection:
    """PostgreSQL database connection manager with connection pooling."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.config.validate_config()
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with connection pooling."""
        try:
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=True,  # Verify connections before use
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
                connect_args={
                    "options": "-c timezone=utc"
                }
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,  # Keep attributes accessible after commit
                bind=self.engine
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection."""
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
        """Get database session with automatic cleanup."""
        from fastapi import HTTPException
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except HTTPException:
            # HTTPExceptions are not database errors - don't rollback
            # They represent valid HTTP error responses
            session.rollback()
            raise
        except Exception as e:
            # Only rollback on actual database/application errors
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_session_dependency(self) -> Generator[Session, None, None]:
        """FastAPI dependency for database sessions."""
        return self.get_session()
    
    def create_tables(self, base):
        """Create all tables defined in the Base metadata."""
        try:
            base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def drop_tables(self, base):
        """Drop all tables defined in the Base metadata."""
        try:
            base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop database tables: {str(e)}")
            raise
    
    def execute_raw_sql(self, sql: str, params: Optional[dict] = None):
        """Execute raw SQL query."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql), params or {})
                connection.commit()
                return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to execute raw SQL: {str(e)}")
            raise
    
    def close(self):
        """Close database engine and cleanup resources."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine closed")


# Global database connection instance
db_connection: Optional[DatabaseConnection] = None


def get_database_connection() -> DatabaseConnection:
    """Get global database connection instance."""
    global db_connection
    if db_connection is None:
        db_connection = DatabaseConnection()
    return db_connection


def initialize_database(config: Optional[DatabaseConfig] = None) -> DatabaseConnection:
    """Initialize database connection."""
    global db_connection
    db_connection = DatabaseConnection(config)
    return db_connection


def close_database():
    """Close global database connection."""
    global db_connection
    if db_connection:
        db_connection.close()
        db_connection = None


# Example usage and testing functions
def test_database_setup():
    """Test database setup and configuration."""
    try:
        db = get_database_connection()
        
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
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Database setup test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run database connection test
    logging.basicConfig(level=logging.INFO)
    test_database_setup()
