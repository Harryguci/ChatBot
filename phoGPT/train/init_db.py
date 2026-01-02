"""
Database initialization script.
Creates all necessary tables for training management.
"""

import logging
from config.db_config import get_db_config, test_database_setup
from models.training_models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize database by creating all tables.
    """
    try:
        logger.info("Starting database initialization...")

        # Test database connection first
        logger.info("Testing database connection...")
        if not test_database_setup():
            logger.error("Database connection test failed. Please check your configuration.")
            return False

        # Get database configuration
        db_config = get_db_config()

        # Create all tables
        logger.info("Creating database tables...")
        db_config.create_tables(Base)

        logger.info("✓ Database initialization completed successfully!")
        logger.info("\nCreated tables:")
        logger.info("  - training_runs")
        logger.info("  - training_metrics")

        return True

    except Exception as e:
        logger.error(f"✗ Database initialization failed: {str(e)}")
        return False


def drop_all_tables():
    """
    Drop all tables (use with caution!).
    """
    try:
        db_config = get_db_config()

        logger.warning("⚠ WARNING: This will drop all training-related tables!")
        confirm = input("Are you sure you want to continue? (yes/no): ")

        if confirm.lower() != "yes":
            logger.info("Operation cancelled.")
            return False

        logger.info("Dropping all tables...")
        db_config.drop_tables(Base)

        logger.info("✓ All tables dropped successfully!")
        return True

    except Exception as e:
        logger.error(f"✗ Failed to drop tables: {str(e)}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_all_tables()
    else:
        init_database()
