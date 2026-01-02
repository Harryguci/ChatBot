# Database Migrations (Python)

This folder contains Python migration files for the training management system.

## Migration Files

Migrations are Python files named with the following convention:
```
YYYYMMDD_NNN_description.py
```

Where:
- `YYYYMMDD` - Date of creation (e.g., 20251228)
- `NNN` - Sequential number (e.g., 001, 002)
- `description` - Brief description of the migration

## Available Migrations

### 20251228_001_initial_schema.py
**Purpose**: Creates the initial database schema for training management

**Tables Created**:
- `training_runs` - Stores training run information
- `training_metrics` - Stores step-by-step metrics

**Indexes Created**:
- `idx_training_runs_run_name` - Fast lookups by run name
- `idx_training_runs_status` - Filter by status
- `idx_training_runs_created_at` - Sort by creation date
- `idx_training_metrics_run_id` - Fast joins with training runs
- `idx_training_metrics_step` - Sort by step
- `idx_training_metrics_run_step` - Composite index for common queries

**Foreign Keys**:
- `training_metrics.training_run_id` → `training_runs.id` (CASCADE delete)

### 20251228_002_example_add_column.py
**Purpose**: Example migration showing how to add columns

This is a template/example migration that demonstrates:
- How to add new columns to existing tables
- How to write upgrade and downgrade functions
- How to use raw SQL for schema changes

## Migration Manager

The `migrate.py` script provides commands to manage migrations.

### Commands

```bash
# Show migration status
python migrations/migrate.py status

# Apply all pending migrations
python migrations/migrate.py upgrade

# Apply migrations up to specific revision
python migrations/migrate.py upgrade 20251228_001

# Rollback last migration
python migrations/migrate.py downgrade

# Rollback last N migrations
python migrations/migrate.py downgrade 2

# Show migration history
python migrations/migrate.py history
```

## Quick Start

### 1. Check Migration Status

```bash
cd phoGPT/train
python migrations/migrate.py status
```

Output:
```
============================================================
MIGRATION STATUS
============================================================

Total migrations: 2
Applied: 0
Pending: 2

Migrations:

  ○ PENDING  20251228_001_initial_schema
           Creates training_runs and training_metrics tables
  ○ PENDING  20251228_002_example_add_column
           Example migration showing how to add a new column

============================================================
```

### 2. Apply Migrations

```bash
python migrations/migrate.py upgrade
```

Output:
```
============================================================
APPLYING MIGRATIONS
============================================================

Found 2 pending migration(s):

  • 20251228_001_initial_schema
  • 20251228_002_example_add_column

Applying 20251228_001_initial_schema...
✓ Migration 20251228_001 applied successfully
  Created tables:
    - training_runs
    - training_metrics
✓ 20251228_001_initial_schema applied

============================================================
✓ All migrations applied successfully
============================================================
```

### 3. Check History

```bash
python migrations/migrate.py history
```

### 4. Rollback (if needed)

```bash
python migrations/migrate.py downgrade
```

## Migration Structure

Each migration file must contain:

### Required Functions

```python
def upgrade(engine):
    """Apply migration changes."""
    # Your upgrade logic here
    pass

def downgrade(engine):
    """Rollback migration changes."""
    # Your downgrade logic here
    pass
```

### Required Metadata

```python
# Revision identifiers
revision = '20251228_001'        # Unique revision ID
down_revision = None              # Previous revision (None for first)
branch_labels = None
depends_on = None
```

## Creating New Migrations

### Step 1: Create Migration File

Create a new file following the naming convention:

```bash
# Example: migrations/20251229_003_add_priority_column.py
```

### Step 2: Write Migration Code

```python
"""
Migration: Add priority column
Created: 2025-12-29
Description: Adds priority field to training_runs table
"""

from sqlalchemy import text

# Revision identifiers
revision = '20251229_003'
down_revision = '20251228_002'  # Previous migration
branch_labels = None
depends_on = None


def upgrade(engine):
    """Add priority column."""
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE training_runs
            ADD COLUMN priority INTEGER DEFAULT 0
        """))
        conn.execute(text("""
            CREATE INDEX idx_training_runs_priority
            ON training_runs(priority)
        """))
        conn.commit()

    print(f"✓ Migration {revision} applied successfully")


def downgrade(engine):
    """Remove priority column."""
    with engine.connect() as conn:
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_training_runs_priority
        """))
        conn.execute(text("""
            ALTER TABLE training_runs
            DROP COLUMN priority
        """))
        conn.commit()

    print(f"✓ Migration {revision} rolled back successfully")
```

### Step 3: Test Migration

```bash
# Apply migration
python migrations/migrate.py upgrade

# Check status
python migrations/migrate.py status

# Test rollback
python migrations/migrate.py downgrade
```

## Migration Best Practices

### 1. Always Test Rollbacks

```bash
# Apply
python migrations/migrate.py upgrade

# Test rollback
python migrations/migrate.py downgrade

# Reapply
python migrations/migrate.py upgrade
```

### 2. Use Transactions

Wrap your changes in transactions for safety:

```python
def upgrade(engine):
    with engine.begin() as conn:  # Automatic transaction
        conn.execute(text("..."))
        conn.execute(text("..."))
```

### 3. Make Migrations Idempotent

Use `IF NOT EXISTS` and `IF EXISTS` clauses:

```python
conn.execute(text("""
    ALTER TABLE training_runs
    ADD COLUMN IF NOT EXISTS new_column TEXT
"""))
```

### 4. Add Comments

Document your changes:

```python
conn.execute(text("""
    COMMENT ON COLUMN training_runs.priority IS 'Training run priority (0-10)'
"""))
```

### 5. Update down_revision

Always set the correct `down_revision` to the previous migration:

```python
revision = '20251229_003'
down_revision = '20251228_002'  # Important!
```

## Common Migration Patterns

### Add Column

```python
def upgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE training_runs
            ADD COLUMN new_field VARCHAR(255)
        """))
        conn.commit()
```

### Add Index

```python
def upgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE INDEX idx_training_runs_field
            ON training_runs(field)
        """))
        conn.commit()
```

### Add Foreign Key

```python
def upgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE table_name
            ADD CONSTRAINT fk_constraint_name
            FOREIGN KEY (column_name)
            REFERENCES other_table(id)
            ON DELETE CASCADE
        """))
        conn.commit()
```

### Modify Column

```python
def upgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE training_runs
            ALTER COLUMN status SET NOT NULL
        """))
        conn.commit()
```

### Rename Column

```python
def upgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE training_runs
            RENAME COLUMN old_name TO new_name
        """))
        conn.commit()
```

## Migration Tracking

Migrations are tracked in the `migration_history` table:

```sql
CREATE TABLE migration_history (
    id SERIAL PRIMARY KEY,
    revision VARCHAR(50) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

View applied migrations:

```sql
SELECT * FROM migration_history ORDER BY applied_at;
```

## Troubleshooting

### "relation already exists"

The migration has already been applied. Check status:

```bash
python migrations/migrate.py status
```

### "permission denied"

Ensure your database user has ALTER TABLE permissions:

```sql
GRANT ALL ON DATABASE chatbot_ocr_db TO postgres;
```

### Migration Failed Midway

If a migration fails:

1. Check the error message
2. Fix the issue in the migration file
3. Manually rollback changes (if needed)
4. Reapply the migration

### Reset Migrations (DANGER!)

To start fresh (⚠️ **WILL DELETE ALL DATA**):

```bash
# Drop all tables
python migrations/migrate.py downgrade 999

# Or manually:
python -c "from config.db_config import get_db_config; from models.training_models import Base; db = get_db_config(); db.drop_tables(Base)"

# Reapply all migrations
python migrations/migrate.py upgrade
```

## Integration with init_db.py

The `init_db.py` script uses SQLAlchemy models directly. For production, prefer using migrations:

**Development:**
```bash
python init_db.py  # Quick setup using ORM models
```

**Production:**
```bash
python migrations/migrate.py upgrade  # Tracked, versioned migrations
```

## Schema Overview

After applying all migrations:

```
training_runs
├── id (PRIMARY KEY)
├── run_name (UNIQUE, INDEXED)
├── model_name
├── dataset_name
├── status (INDEXED)
├── hyperparameters (JSON)
├── learning_rate
├── batch_size
├── num_epochs
├── max_steps
├── current_epoch
├── current_step
├── progress_percentage
├── train_loss
├── eval_loss
├── best_metric
├── created_at (INDEXED DESC)
├── started_at
├── completed_at
├── updated_at
├── output_dir
├── error_message
└── notes

training_metrics
├── id (PRIMARY KEY)
├── training_run_id (FOREIGN KEY, INDEXED)
├── step (UNIQUE with training_run_id)
├── epoch
├── loss
├── eval_loss
├── learning_rate
├── gradient_norm
├── metrics (JSON)
└── created_at

migration_history (system table)
├── id (PRIMARY KEY)
├── revision (UNIQUE)
└── applied_at
```

## Examples

### Apply All Migrations

```bash
python migrations/migrate.py upgrade
```

### Rollback Last 2 Migrations

```bash
python migrations/migrate.py downgrade 2
```

### Check What Will Be Applied

```bash
python migrations/migrate.py status
```

### View History

```bash
python migrations/migrate.py history
```

## Next Steps

1. **Check status**: `python migrations/migrate.py status`
2. **Apply migrations**: `python migrations/migrate.py upgrade`
3. **Verify tables**: Check database or use `init_db.py --drop` then migrate
4. **Create new migrations**: Follow the template in `20251228_002_example_add_column.py`
