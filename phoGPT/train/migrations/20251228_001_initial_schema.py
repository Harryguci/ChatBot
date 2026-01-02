"""
Migration: Initial schema for training management
Created: 2025-12-28
Description: Creates training_runs and training_metrics tables
"""

from sqlalchemy import (
    Table, Column, Integer, String, Float, JSON,
    DateTime, Text, ForeignKey, Index, text
)
from sqlalchemy.sql import func
from sqlalchemy.schema import MetaData

# Revision identifiers
revision = '20251228_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade(engine):
    """
    Apply migration: Create training_runs and training_metrics tables.

    Args:
        engine: SQLAlchemy engine instance
    """
    metadata = MetaData()

    # Create training_runs table
    training_runs = Table(
        'training_runs',
        metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('run_name', String(255), nullable=False, unique=True, index=True),
        Column('model_name', String(255), nullable=False),
        Column('dataset_name', String(255), nullable=False),

        # Status tracking
        Column('status', String(50), nullable=False, server_default='pending'),

        # Hyperparameters (stored as JSON)
        Column('hyperparameters', JSON),

        # Key hyperparameters (duplicated for easy querying)
        Column('learning_rate', Float),
        Column('batch_size', Integer),
        Column('num_epochs', Integer),
        Column('max_steps', Integer),

        # Progress tracking
        Column('current_epoch', Integer, server_default='0'),
        Column('current_step', Integer, server_default='0'),
        Column('progress_percentage', Float, server_default='0.0'),

        # Metrics
        Column('train_loss', Float),
        Column('eval_loss', Float),
        Column('best_metric', Float),

        # Timestamps
        Column('created_at', DateTime(timezone=True), server_default=func.now()),
        Column('started_at', DateTime(timezone=True)),
        Column('completed_at', DateTime(timezone=True)),
        Column('updated_at', DateTime(timezone=True)),

        # Output and notes
        Column('output_dir', Text),
        Column('error_message', Text),
        Column('notes', Text),
    )

    # Create indexes for training_runs
    Index('idx_training_runs_status', training_runs.c.status)
    Index('idx_training_runs_created_at', training_runs.c.created_at.desc())

    # Create training_metrics table
    training_metrics = Table(
        'training_metrics',
        metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('training_run_id', Integer, ForeignKey('training_runs.id', ondelete='CASCADE'), nullable=False),

        # Step and epoch
        Column('step', Integer, nullable=False),
        Column('epoch', Integer),

        # Metrics
        Column('loss', Float),
        Column('eval_loss', Float),
        Column('learning_rate', Float),
        Column('gradient_norm', Float),

        # Additional metrics (stored as JSON)
        Column('metrics', JSON),

        # Timestamp
        Column('created_at', DateTime(timezone=True), server_default=func.now()),
    )

    # Create indexes for training_metrics
    Index('idx_training_metrics_run_id', training_metrics.c.training_run_id)
    Index('idx_training_metrics_step', training_metrics.c.step)
    Index('idx_training_metrics_run_step', training_metrics.c.training_run_id, training_metrics.c.step.desc())

    # Unique constraint: one metric per step per training run
    Index('uq_training_metrics_run_step', training_metrics.c.training_run_id, training_metrics.c.step, unique=True)

    # Create all tables
    metadata.create_all(engine)

    # Add table comments using raw SQL
    with engine.connect() as conn:
        conn.execute(text("""
            COMMENT ON TABLE training_runs IS 'Stores information about training runs'
        """))
        conn.execute(text("""
            COMMENT ON TABLE training_metrics IS 'Stores step-by-step metrics for training runs'
        """))
        conn.execute(text("""
            COMMENT ON COLUMN training_runs.status IS 'Current status: pending, running, completed, failed, cancelled'
        """))
        conn.execute(text("""
            COMMENT ON COLUMN training_runs.hyperparameters IS 'Full hyperparameters configuration as JSON'
        """))
        conn.execute(text("""
            COMMENT ON COLUMN training_runs.progress_percentage IS 'Training progress from 0 to 100'
        """))
        conn.execute(text("""
            COMMENT ON COLUMN training_metrics.metrics IS 'Additional custom metrics as JSON'
        """))
        conn.commit()

    print(f"[OK] Migration {revision} applied successfully")
    print("  Created tables:")
    print("    - training_runs")
    print("    - training_metrics")


def downgrade(engine):
    """
    Rollback migration: Drop training_runs and training_metrics tables.

    Args:
        engine: SQLAlchemy engine instance
    """
    metadata = MetaData()

    # Define tables (order matters due to foreign keys)
    training_metrics = Table('training_metrics', metadata)
    training_runs = Table('training_runs', metadata)

    # Drop tables in reverse order
    metadata.drop_all(engine, tables=[training_metrics, training_runs])

    print(f"[OK] Migration {revision} rolled back successfully")
    print("  Dropped tables:")
    print("    - training_metrics")
    print("    - training_runs")


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
    print(f"Description: Creates training_runs and training_metrics tables\n")

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
