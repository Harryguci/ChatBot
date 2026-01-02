# Python Migration System - Quick Guide

## Overview

This migration system provides version-controlled database schema changes using Python files instead of raw SQL.

## Key Files

- `migrate.py` - Migration runner with CLI commands
- `202512 28_001_initial_schema.py` - Initial schema migration
- `20251228_002_example_add_column.py` - Example template migration
- `migration_history` table - Tracks applied migrations

## Quick Commands

```bash
# Check status
python migrations/migrate.py status

# Apply all migrations
python migrations/migrate.py upgrade

# Rollback last migration
python migrations/migrate.py downgrade

# View history
python migrations/migrate.py history
```

## Current Status

Since you already ran `init_db.py`, the tables exist but migrations are marked as pending. You have two options:

### Option 1: Continue with init_db.py (Recommended for Development)

```bash
# Keep using init_db.py for quick development
python init_db.py
```

### Option 2: Track with Migrations (Recommended for Production)

```bash
# Mark existing tables as migrated (without recreating them)
# This syncs the migration history with current state

python -c "from migrations.migrate import MigrationManager; m = MigrationManager(); m._mark_migration_applied('20251228_001_initial_schema')"
```

## Creating New Migrations

### 1. Create File

```bash
# Create: migrations/20251229_003_add_user_field.py
```

### 2. Write Migration

```python
"""
Migration: Add user field to training runs
Created: 2025-12-29
Description: Adds user_id column to track who created each run
"""

from sqlalchemy import text

revision = '20251229_003'
down_revision = '20251228_002'  # Previous migration


def upgrade(engine):
    """Add user_id column."""
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE training_runs
            ADD COLUMN IF NOT EXISTS user_id INTEGER
        """))
        conn.commit()
    print(f"[OK] Migration {revision} applied")


def downgrade(engine):
    """Remove user_id column."""
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE training_runs
            DROP COLUMN IF EXISTS user_id
        """))
        conn.commit()
    print(f"[OK] Migration {revision} rolled back")
```

### 3. Apply Migration

```bash
python migrations/migrate.py upgrade
```

## Migration vs init_db.py

| Feature | init_db.py | Migrations |
|---------|-----------|------------|
| **Speed** | Fast | Slower (tracked) |
| **Tracking** | No history | Full history |
| **Rollback** | Manual | Automatic |
| **Production** | Not recommended | Recommended |
| **Development** | Perfect | Overkill |

## Best Practices

1. **Development**: Use `init_db.py` for quick iteration
2. **Production**: Use migrations for tracked, versioned changes
3. **Team**: Use migrations to sync schema across developers
4. **Testing**: Use migrations to ensure reproducible database state

## Common Patterns

### Add Column
```python
conn.execute(text("ALTER TABLE table_name ADD COLUMN col_name TYPE"))
```

### Add Index
```python
conn.execute(text("CREATE INDEX idx_name ON table_name(column)"))
```

### Add Foreign Key
```python
conn.execute(text("""
    ALTER TABLE table_name
    ADD CONSTRAINT fk_name
    FOREIGN KEY (col) REFERENCES other_table(id)
"""))
```

## Troubleshooting

### Tables already exist
```bash
# Option 1: Drop and recreate
python init_db.py --drop
python migrations/migrate.py upgrade

# Option 2: Mark as applied
python -c "from migrations.migrate import MigrationManager; m = MigrationManager(); m._mark_migration_applied('20251228_001_initial_schema')"
```

### Check what's applied
```bash
python migrations/migrate.py history
```

### Reset everything
```bash
python init_db.py --drop
python migrations/migrate.py upgrade
```

## Full Documentation

See [README.md](README.md) for complete documentation.
