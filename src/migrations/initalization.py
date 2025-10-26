"""
Database initialization migration for PostgreSQL.

This module provides functionality to initialize the database schema
with all required tables, indexes, and constraints.

Usage:
    python src/migrations/initalization.py
    
    Or import and use programmatically:
    from src.migrations.initalization import initialize_database
    initialize_database()
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.db.db_connection import get_database_connection, initialize_database, DatabaseConfig
from src.config.db.db_init import DatabaseInitializer
from src.config.db.models import Base
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_extension_if_not_exists(db, extension_name: str = "pgcrypto"):
    """
    Create PostgreSQL extension if it doesn't exist.
    
    Args:
        db: Database connection instance
        extension_name: Name of the extension to create (default: pgcrypto for hash functions)
    """
    try:
        with db.get_session() as session:
            # Check if extension exists
            result = session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = :extname"),
                {"extname": extension_name}
            )
            
            if not result.first():
                # Create extension
                session.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension_name}"))
                session.commit()
                logger.info(f"✓ Created PostgreSQL extension: {extension_name}")
            else:
                logger.info(f"✓ Extension {extension_name} already exists")
                
    except SQLAlchemyError as e:
        logger.error(f"Failed to create extension {extension_name}: {str(e)}")
        raise


def create_tables(db):
    """
    Create all database tables.
    
    Args:
        db: Database connection instance
    """
    try:
        logger.info("Creating database tables...")
        
        # Simply create all tables - if they exist, checkfirst will skip them
        # If indexes exist, we'll catch the error and continue
        try:
            Base.metadata.create_all(bind=db.engine, checkfirst=True)
            logger.info("✓ All tables created successfully")
        except SQLAlchemyError as e:
            # Check if the error is about duplicate indexes
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.warning(f"Some database objects already exist: {str(e)}")
                logger.info("Continuing with verification...")
                return True
            else:
                # Re-raise if it's a different error
                raise
        
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to create tables: {str(e)}")
        raise


def verify_tables(db):
    """
    Verify that all expected tables exist.
    
    Args:
        db: Database connection instance
        
    Returns:
        bool: True if all tables exist, False otherwise
    """
    expected_tables = [
        'users',
        'documents',
        'document_chunks',
        'conversations',
        'messages',
        'chatbot_sessions',
        'embedding_cache',
        'system_logs'
    ]
    
    try:
        with db.get_session() as session:
            # Query existing tables
            result = session.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            
            existing_tables = {row[0] for row in result.fetchall()}
            
            missing_tables = set(expected_tables) - existing_tables
            
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False
            
            logger.info(f"✓ All {len(expected_tables)} tables verified")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Failed to verify tables: {str(e)}")
        return False


def verify_indexes(db):
    """
    Verify that critical indexes exist.
    
    Args:
        db: Database connection instance
        
    Returns:
        bool: True if indexes are properly created
    """
    critical_indexes = [
        ('users', 'ix_users_username'),
        ('users', 'ix_users_email'),
        ('conversations', 'ix_conversations_session_id'),
        ('chatbot_sessions', 'ix_chatbot_sessions_session_id'),
        ('embedding_cache', 'ix_embedding_cache_content_hash'),
        ('document_chunks', 'ix_document_chunks_embedding_cosine'),
        ('document_chunks', 'ix_document_chunks_vintern_embedding_cosine'),
    ]
    
    try:
        with db.get_session() as session:
            for table, index_name in critical_indexes:
                result = session.execute(
                    text("""
                        SELECT 1 
                        FROM pg_indexes 
                        WHERE tablename = :table AND indexname = :index
                    """),
                    {"table": table, "index": index_name}
                )
                
                if not result.first():
                    logger.warning(f"Missing index: {index_name} on table {table}")
                    return False
            
            logger.info("✓ All critical indexes verified")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Failed to verify indexes: {str(e)}")
        return False


def initialize_migration():
    """
    Initialize the database with all required schema.
    
    This function:
    1. Creates database if it doesn't exist
    2. Tests the database connection
    3. Creates PostgreSQL extensions if needed
    4. Creates all tables
    5. Verifies tables and indexes
    
    Returns:
        bool: True if initialization was successful
    """
    try:
        logger.info("=" * 60)
        logger.info("Starting database initialization...")
        logger.info("=" * 60)
        
        # Create database if it doesn't exist
        logger.info("\nCreating database if it doesn't exist...")
        config = DatabaseConfig()
        initializer = DatabaseInitializer(config)
        
        if not initializer.create_database():
            logger.error("Failed to create database")
            return False
        
        # Initialize database connection
        db = initialize_database()
        
        # Test connection
        logger.info("Testing database connection...")
        if not db.test_connection():
            logger.error("Database connection test failed")
            return False
        logger.info("✓ Database connection successful")
        
        # Create extensions
        logger.info("\nCreating PostgreSQL extensions...")
        create_extension_if_not_exists(db, "pgcrypto")
        create_extension_if_not_exists(db, "vector")  # pgvector for vector similarity search
        
        # Create tables
        logger.info("\nCreating database tables...")
        create_tables(db)
        
        # Verify tables
        logger.info("\nVerifying database schema...")
        if not verify_tables(db):
            logger.error("Table verification failed")
            return False
        
        # Verify indexes
        if not verify_indexes(db):
            logger.warning("Some indexes may be missing, but continuing...")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Database initialization completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Database initialization failed: {str(e)}")
        logger.exception("Full error trace:")
        return False


def rollback_migration():
    """
    Rollback the database schema (drop all tables).
    
    WARNING: This will delete all data in the database!
    
    Returns:
        bool: True if rollback was successful
    """
    try:
        logger.warning("=" * 60)
        logger.warning("ROLLBACK: Dropping all database tables...")
        logger.warning("WARNING: This will delete all data!")
        logger.warning("=" * 60)
        
        db = get_database_connection()
        # Use checkfirst=True to handle missing tables gracefully
        with db.engine.connect() as connection:
            Base.metadata.drop_all(bind=db.engine, checkfirst=True)
        
        logger.info("✓ All tables dropped successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to rollback database: {str(e)}")
        return False


def main():
    """Main entry point for the migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Database initialization migration for PostgreSQL'
    )
    parser.add_argument(
        'action',
        nargs='?',
        choices=['init', 'rollback', 'verify'],
        default='init',
        help='Action to perform: init (initialize), rollback (drop tables), or verify (check schema)'
    )
    
    args = parser.parse_args()
    
    if args.action == 'init':
        success = initialize_migration()
        sys.exit(0 if success else 1)
    
    elif args.action == 'rollback':
        # Confirmation prompt
        confirm = input("\nAre you sure you want to drop all tables? (yes/no): ")
        if confirm.lower() == 'yes':
            success = rollback_migration()
            sys.exit(0 if success else 1)
        else:
            logger.info("Rollback cancelled")
            sys.exit(0)
    
    elif args.action == 'verify':
        db = get_database_connection()
        tables_ok = verify_tables(db)
        indexes_ok = verify_indexes(db)
        
        if tables_ok and indexes_ok:
            logger.info("\n✓ Database schema is valid")
            sys.exit(0)
        else:
            logger.error("\n✗ Database schema verification failed")
            sys.exit(1)


if __name__ == "__main__":
    main()