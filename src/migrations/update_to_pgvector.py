"""
Migration script to update database schema to use pgvector for embeddings.

This script:
1. Installs pgvector extension
2. Removes content_hash column from documents table
3. Converts embedding and vintern_embedding columns from JSON to Vector type
4. Creates vector similarity indexes

Usage:
    python src/migrations/update_to_pgvector.py
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


def install_pgvector_extension(db):
    """Install pgvector extension if not already installed."""
    try:
        with db.get_session() as session:
            result = session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            
            if not result.first():
                logger.info("Installing pgvector extension...")
                session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                session.commit()
                logger.info("✓ pgvector extension installed successfully")
            else:
                logger.info("✓ pgvector extension already exists")
                
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to install pgvector extension: {str(e)}")
        raise


def migrate_to_vector(db):
    """Migrate embeddings from JSON to Vector type."""
    try:
        logger.info("Starting vector migration...")
        
        with db.get_session() as session:
            # Step 1: Check if vector column exists
            result = session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'document_chunks' AND column_name = 'embedding'
            """))
            col_info = result.fetchone()
            
            if col_info and col_info[1] == 'USER-DEFINED':
                logger.info("✓ Embeddings already using vector type")
                return True
            
            # Step 2: Create new vector columns
            logger.info("Creating vector columns...")
            session.execute(text("""
                ALTER TABLE document_chunks 
                ADD COLUMN IF NOT EXISTS embedding_new vector(384)
            """))
            session.execute(text("""
                ALTER TABLE document_chunks 
                ADD COLUMN IF NOT EXISTS vintern_embedding_new vector(768)
            """))
            session.commit()
            
            # Step 3: Migrate data
            logger.info("Migrating embedding data...")
            session.execute(text("""
                UPDATE document_chunks
                SET embedding_new = CAST(embedding::text AS vector)
                WHERE embedding IS NOT NULL AND embedding::text IS NOT NULL
            """))
            
            logger.info("Migrating vintern_embedding data...")
            session.execute(text("""
                UPDATE document_chunks
                SET vintern_embedding_new = CAST(vintern_embedding::text AS vector)
                WHERE vintern_embedding IS NOT NULL AND vintern_embedding::text IS NOT NULL
            """))
            session.commit()
            
            # Step 4: Drop old columns and rename new ones
            logger.info("Updating column definitions...")
            session.execute(text("""
                ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding
            """))
            session.execute(text("""
                ALTER TABLE document_chunks DROP COLUMN IF EXISTS vintern_embedding
            """))
            session.execute(text("""
                ALTER TABLE document_chunks RENAME COLUMN embedding_new TO embedding
            """))
            session.execute(text("""
                ALTER TABLE document_chunks RENAME COLUMN vintern_embedding_new TO vintern_embedding
            """))
            session.commit()
            
            # Step 5: Create vector indexes
            logger.info("Creating vector indexes...")
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_cosine 
                ON document_chunks USING ivfflat (embedding vector_cosine_ops)
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_document_chunks_vintern_embedding_cosine 
                ON document_chunks USING ivfflat (vintern_embedding vector_cosine_ops)
            """))
            session.commit()
            
            logger.info("✓ Vector migration completed successfully")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Failed to migrate to vector: {str(e)}")
        raise


def remove_content_hash(db):
    """Remove content_hash column from documents table."""
    try:
        logger.info("Removing content_hash column...")
        
        with db.get_session() as session:
            # Check if content_hash exists
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'content_hash'
            """))
            
            if result.fetchone():
                # Drop index first
                session.execute(text("""
                    DROP INDEX IF EXISTS ix_documents_content_hash
                """))
                
                # Drop column
                session.execute(text("""
                    ALTER TABLE documents DROP COLUMN content_hash
                """))
                
                session.commit()
                logger.info("✓ content_hash column removed successfully")
            else:
                logger.info("✓ content_hash column does not exist")
        
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to remove content_hash: {str(e)}")
        logger.warning("Continuing anyway...")


def migrate_database():
    """Main migration function."""
    try:
        logger.info("=" * 60)
        logger.info("Starting database migration to pgvector...")
        logger.info("=" * 60)
        
        db = get_database_connection()
        
        # Test connection
        if not db.test_connection():
            logger.error("Database connection test failed")
            return False
        
        # Install pgvector extension
        install_pgvector_extension(db)
        
        # Remove content_hash
        remove_content_hash(db)
        
        # Migrate to vector type
        migrate_to_vector(db)
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Database migration completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Database migration failed: {str(e)}")
        logger.exception("Full error trace:")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Update database to use pgvector for embeddings'
    )
    
    args = parser.parse_args()
    
    success = migrate_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

