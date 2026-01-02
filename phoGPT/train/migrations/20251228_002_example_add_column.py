"""
Migration: Example - Add new column to training_runs
Created: 2025-12-28
Description: Example migration showing how to add a new column
"""

from sqlalchemy import text

# Revision identifiers
revision = '20251228_002'
down_revision = '20251228_001'
branch_labels = None
depends_on = None


def upgrade(engine):
    """
    Apply migration: Add example column to training_runs.

    This is an example migration to demonstrate how to modify existing tables.
    You can use this as a template for future schema changes.

    Args:
        engine: SQLAlchemy engine instance
    """
    with engine.connect() as conn:
        # Example: Add a new column
        # Uncomment to apply:
        # conn.execute(text("""
        #     ALTER TABLE training_runs
        #     ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0
        # """))
        # conn.commit()

        print(f"[OK] Migration {revision} applied successfully")
        print("  (This is an example migration - no changes made)")


def downgrade(engine):
    """
    Rollback migration: Remove example column from training_runs.

    Args:
        engine: SQLAlchemy engine instance
    """
    with engine.connect() as conn:
        # Example: Remove the column
        # Uncomment to apply:
        # conn.execute(text("""
        #     ALTER TABLE training_runs
        #     DROP COLUMN IF EXISTS priority
        # """))
        # conn.commit()

        print(f"[OK] Migration {revision} rolled back successfully")
        print("  (This is an example migration - no changes made)")


if __name__ == "__main__":
    """
    Run migration directly for testing.
    """
    import sys
    from pathlib import Path

    # Add parent directory to path so we can import config
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config.db_config import get_db_config

    print(f"\nRunning migration: {revision}")
    print(f"Description: Example migration\n")

    db_config = get_db_config()
    engine = db_config.engine

    if engine is None:
        print("[ERROR] Failed to get database engine")
        exit(1)

    # Apply migration
    try:
        upgrade(engine)
    except Exception as e:
        print(f"[ERROR] Migration failed: {str(e)}")
        exit(1)
