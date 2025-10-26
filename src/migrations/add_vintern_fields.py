"""
Migration script to add Vintern embedding fields to document_chunks table.
Run this script to update the database schema.
"""

import logging
from sqlalchemy import text
from src.config.db.db_connection import get_database_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_vintern_fields():
    """Add vintern_embedding and vintern_model columns to document_chunks table."""
    try:
        db = get_database_connection()
        
        with db.engine.connect() as connection:
            # Check if columns already exist
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='document_chunks' 
                AND column_name IN ('vintern_embedding', 'vintern_model')
            """)
            result = connection.execute(check_query)
            existing_columns = {row[0] for row in result}
            
            # Add vintern_embedding column if not exists
            if 'vintern_embedding' not in existing_columns:
                logger.info("Adding vintern_embedding column...")
                connection.execute(text("""
                    ALTER TABLE document_chunks 
                    ADD COLUMN vintern_embedding JSON
                """))
                connection.commit()
                logger.info("✓ Added vintern_embedding column")
            else:
                logger.info("vintern_embedding column already exists")
            
            # Add vintern_model column if not exists
            if 'vintern_model' not in existing_columns:
                logger.info("Adding vintern_model column...")
                connection.execute(text("""
                    ALTER TABLE document_chunks 
                    ADD COLUMN vintern_model VARCHAR(255)
                """))
                connection.commit()
                logger.info("✓ Added vintern_model column")
            else:
                logger.info("vintern_model column already exists")
        
        logger.info("Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    add_vintern_fields()
