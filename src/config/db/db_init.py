"""
Database initialization and migration utilities.
"""

import os
import logging
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

from .db_connection import DatabaseConfig, DatabaseConnection

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Database initialization and setup utilities."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
    
    def create_database(self) -> bool:
        """Create database if it doesn't exist."""
        try:
            # Connect to PostgreSQL server (not specific database)
            server_url = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/postgres"
            engine = create_engine(server_url)
            
            with engine.connect() as connection:
                # Check if database exists
                result = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": self.config.database}
                )
                
                if not result.fetchone():
                    # Create database
                    connection.execute(text("COMMIT"))  # End transaction
                    connection.execute(text(f"CREATE DATABASE {self.config.database}"))
                    logger.info(f"Database '{self.config.database}' created successfully")
                else:
                    logger.info(f"Database '{self.config.database}' already exists")
            
            engine.dispose()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database: {str(e)}")
            return False
    
    def drop_database(self) -> bool:
        """Drop database if it exists."""
        try:
            # Connect to PostgreSQL server (not specific database)
            server_url = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port}/postgres"
            engine = create_engine(server_url)
            
            with engine.connect() as connection:
                # Check if database exists
                result = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": self.config.database}
                )
                
                if result.fetchone():
                    # Terminate connections to the database
                    connection.execute(text("COMMIT"))
                    connection.execute(
                        text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :db_name"),
                        {"db_name": self.config.database}
                    )
                    # Drop database
                    connection.execute(text(f"DROP DATABASE {self.config.database}"))
                    logger.info(f"Database '{self.config.database}' dropped successfully")
                else:
                    logger.info(f"Database '{self.config.database}' does not exist")
            
            engine.dispose()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop database: {str(e)}")
            return False
    
    def test_database_connection(self) -> bool:
        """Test connection to the specific database."""
        try:
            db = DatabaseConnection(self.config)
            success = db.test_connection()
            db.close()
            return success
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    def setup_database(self) -> bool:
        """Complete database setup: create database and test connection."""
        logger.info("Starting database setup...")
        
        # Create database
        if not self.create_database():
            return False
        
        # Test connection
        if not self.test_database_connection():
            return False
        
        logger.info("Database setup completed successfully")
        return True


def initialize_database_from_env() -> bool:
    """Initialize database using environment variables."""
    config = DatabaseConfig()
    initializer = DatabaseInitializer(config)
    return initializer.setup_database()


def create_database_from_env() -> bool:
    """Create database using environment variables."""
    config = DatabaseConfig()
    initializer = DatabaseInitializer(config)
    return initializer.create_database()


def drop_database_from_env() -> bool:
    """Drop database using environment variables."""
    config = DatabaseConfig()
    initializer = DatabaseInitializer(config)
    return initializer.drop_database()


if __name__ == "__main__":
    """Command line interface for database management."""
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python db_init.py [create|drop|setup|test]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "create":
        success = create_database_from_env()
        sys.exit(0 if success else 1)
    elif command == "drop":
        success = drop_database_from_env()
        sys.exit(0 if success else 1)
    elif command == "setup":
        success = initialize_database_from_env()
        sys.exit(0 if success else 1)
    elif command == "test":
        config = DatabaseConfig()
        initializer = DatabaseInitializer(config)
        success = initializer.test_database_connection()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        print("Available commands: create, drop, setup, test")
        sys.exit(1)
