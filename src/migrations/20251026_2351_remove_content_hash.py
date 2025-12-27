"""
Migration script to remove content_hash column from documents table.

This migration:
1. Drops the unique index on content_hash
2. Drops the content_hash column from documents table

Run this after migrating to pgvector to clean up the old schema.

Usage:
    python src/migrations/20251026_2351_remove_content_hash.py
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.db.db_connection import get_database_connection
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def remove_content_hash_column(db):
    """
    Remove content_hash column and its index from documents table.
    
    Args:
        db: Database connection instance
    """
    try:
        logger.info("Removing content_hash column and index...")
        
        with db.get_session() as session:
            # Step 1: Drop the unique index on content_hash
            logger.info("Dropping index ix_documents_content_hash...")
            session.execute(text("DROP INDEX IF EXISTS ix_documents_content_hash CASCADE"))
            session.commit()
            logger.info("✓ Index dropped")
            
            # Step 2: Check if content_hash column exists
            logger.info("Checking if content_hash column exists...")
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'content_hash'
            """))
            
            if result.first():
                logger.info("Dropping content_hash column...")
                session.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS content_hash CASCADE"))
                session.commit()
                logger.info("✓ Column dropped successfully")
            else:
                logger.info("✓ content_hash column does not exist")
        
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to remove content_hash: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Full error trace:")
        raise


def verify_migration(db):
    """
    Verify that content_hash has been removed.
    
    Args:
        db: Database connection instance
        
    Returns:
        bool: True if migration successful
    """
    try:
        with db.get_session() as session:
            # Check if content_hash column still exists
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'content_hash'
            """))
            
            if result.first():
                logger.error("❌ content_hash column still exists!")
                return False
            
            # Check that other required columns exist
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name IN ('id', 'filename', 'original_filename', 'file_type', 'processing_status')
            """))
            
            columns = [row[0] for row in result.fetchall()]
            required = {'id', 'filename', 'original_filename', 'file_type', 'processing_status'}
            
            if not required.issubset(set(columns)):
                logger.error(f"❌ Missing required columns. Found: {columns}")
                return False
            
            logger.info("✓ Migration verification successful")
            return True
            
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return False


def run_migration():
    """Main migration function."""
    try:
        logger.info("=" * 60)
        logger.info("Removing content_hash column from documents table...")
        logger.info("=" * 60)
        
        # Get database connection
        db = get_database_connection()
        
        # Test connection
        if not db.test_connection():
            logger.error("Database connection test failed")
            return False
        
        # Run migration
        remove_content_hash_column(db)
        
        # Verify migration
        if verify_migration(db):
            logger.info("\n" + "=" * 60)
            logger.info("✓ Migration completed successfully!")
            logger.info("=" * 60)
            return True
        else:
            logger.error("\n" + "=" * 60)
            logger.error("✗ Migration verification failed")
            logger.error("=" * 60)
            return False
        
    except Exception as e:
        logger.error(f"\n✗ Migration failed: {str(e)}")
        logger.exception("Full error trace:")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Remove content_hash column from documents table'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("Would remove:")
        logger.info("  - Index: ix_documents_content_hash")
        logger.info("  - Column: documents.content_hash")
        return
    
    success = run_migration()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
