"""
Database migration to add authentication fields to users table.

This migration adds the following fields to support Google OAuth authentication:
- google_id: Google OAuth unique identifier
- picture_url: User's profile picture URL
- role: User role (admin/user)
- is_verified: Email verification status
- last_login: Last login timestamp

Usage:
    python src/migrations/add_auth_fields.py
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.db.db_connection import get_database_connection, initialize_database
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migration():
    """
    Add authentication fields to users table.
    """
    try:
        # Initialize database connection
        db = initialize_database()

        if not db.test_connection():
            logger.error("Failed to connect to database")
            return False

        logger.info("Starting authentication fields migration...")

        with db.get_session() as session:
            # Check if users table exists
            result = session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'users'
                    );
                """)
            )
            table_exists = result.scalar()

            if not table_exists:
                logger.error("Users table does not exist. Run initialization migration first.")
                return False

            logger.info("Users table found. Adding authentication fields...")

            # Add google_id column
            try:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;
                """))
                logger.info("✓ Added google_id column")
            except SQLAlchemyError as e:
                logger.warning(f"google_id column may already exist: {e}")

            # Add picture_url column
            try:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS picture_url VARCHAR(500);
                """))
                logger.info("✓ Added picture_url column")
            except SQLAlchemyError as e:
                logger.warning(f"picture_url column may already exist: {e}")

            # Add role column with default value
            try:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user' NOT NULL;
                """))
                logger.info("✓ Added role column")
            except SQLAlchemyError as e:
                logger.warning(f"role column may already exist: {e}")

            # Add is_verified column
            try:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE NOT NULL;
                """))
                logger.info("✓ Added is_verified column")
            except SQLAlchemyError as e:
                logger.warning(f"is_verified column may already exist: {e}")

            # Add last_login column
            try:
                session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
                """))
                logger.info("✓ Added last_login column")
            except SQLAlchemyError as e:
                logger.warning(f"last_login column may already exist: {e}")

            # Modify email column to be NOT NULL (if it isn't already)
            try:
                session.execute(text("""
                    ALTER TABLE users
                    ALTER COLUMN email SET NOT NULL;
                """))
                logger.info("✓ Updated email column to NOT NULL")
            except SQLAlchemyError as e:
                logger.warning(f"email column may already be NOT NULL: {e}")

            # Create indexes for new columns
            try:
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_google_id
                    ON users (google_id);
                """))
                logger.info("✓ Created index on google_id")
            except SQLAlchemyError as e:
                logger.warning(f"google_id index may already exist: {e}")

            try:
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_role
                    ON users (role);
                """))
                logger.info("✓ Created index on role")
            except SQLAlchemyError as e:
                logger.warning(f"role index may already exist: {e}")

            # Commit all changes
            session.commit()
            logger.info("✅ Authentication fields migration completed successfully!")

            # Display updated table structure
            result = session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position;
            """))

            logger.info("\nUpdated users table structure:")
            for row in result:
                logger.info(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")

            return True

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        return False


def rollback_migration():
    """
    Rollback authentication fields migration (remove added columns).
    """
    try:
        db = initialize_database()

        if not db.test_connection():
            logger.error("Failed to connect to database")
            return False

        logger.info("Rolling back authentication fields migration...")

        with db.get_session() as session:
            # Remove added columns
            session.execute(text("""
                ALTER TABLE users
                DROP COLUMN IF EXISTS google_id,
                DROP COLUMN IF EXISTS picture_url,
                DROP COLUMN IF EXISTS role,
                DROP COLUMN IF EXISTS is_verified,
                DROP COLUMN IF EXISTS last_login;
            """))

            # Make email nullable again (optional)
            session.execute(text("""
                ALTER TABLE users
                ALTER COLUMN email DROP NOT NULL;
            """))

            session.commit()
            logger.info("✅ Authentication fields migration rolled back successfully!")
            return True

    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Authentication fields migration")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (remove auth fields)"
    )

    args = parser.parse_args()

    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()

    sys.exit(0 if success else 1)
