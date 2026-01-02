"""
Migration runner for PhoGPT training database.

Usage:
    python migrations/migrate.py upgrade    # Apply all pending migrations
    python migrations/migrate.py downgrade  # Rollback last migration
    python migrations/migrate.py status     # Show migration status
    python migrations/migrate.py history    # Show migration history
"""

import sys
import os
import importlib.util
from pathlib import Path
from typing import List, Tuple, Optional
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.db_config import get_db_config


class MigrationManager:
    """Manages database migrations."""

    def __init__(self):
        self.db_config = get_db_config()
        self.engine = self.db_config.engine
        self.migrations_dir = Path(__file__).parent
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """Create migration tracking table if it doesn't exist."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id SERIAL PRIMARY KEY,
                    revision VARCHAR(50) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

    def _get_migration_files(self) -> List[Tuple[str, Path]]:
        """
        Get all migration files sorted by revision.

        Returns:
            List of (revision, file_path) tuples
        """
        migrations = []
        for file in sorted(self.migrations_dir.glob('202*_*.py')):
            revision = file.stem
            migrations.append((revision, file))
        return migrations

    def _load_migration_module(self, file_path: Path):
        """Load migration module from file."""
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _get_applied_migrations(self) -> List[str]:
        """Get list of applied migration revisions."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT revision FROM migration_history ORDER BY applied_at
            """))
            return [row[0] for row in result]

    def _mark_migration_applied(self, revision: str):
        """Mark migration as applied in history."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO migration_history (revision)
                VALUES (:revision)
            """), {"revision": revision})
            conn.commit()

    def _mark_migration_unapplied(self, revision: str):
        """Remove migration from history."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM migration_history WHERE revision = :revision
            """), {"revision": revision})
            conn.commit()

    def upgrade(self, target: Optional[str] = None):
        """
        Apply all pending migrations up to target.

        Args:
            target: Target revision (default: latest)
        """
        print("\n" + "=" * 60)
        print("APPLYING MIGRATIONS")
        print("=" * 60 + "\n")

        migrations = self._get_migration_files()
        applied = self._get_applied_migrations()

        # Find pending migrations
        pending = [
            (rev, path) for rev, path in migrations
            if rev not in applied
        ]

        if not pending:
            print("[OK] No pending migrations")
            return

        print(f"Found {len(pending)} pending migration(s):\n")
        for rev, _ in pending:
            print(f"  • {rev}")
        print()

        # Apply migrations
        for revision, file_path in pending:
            print(f"Applying {revision}...")

            try:
                module = self._load_migration_module(file_path)
                module.upgrade(self.engine)
                self._mark_migration_applied(revision)
                print(f"[OK] {revision} applied\n")

                # Stop if we reached target
                if target and revision == target:
                    break

            except Exception as e:
                print(f"[ERROR] Failed to apply {revision}: {str(e)}")
                raise

        print("=" * 60)
        print("[OK] All migrations applied successfully")
        print("=" * 60 + "\n")

    def downgrade(self, steps: int = 1):
        """
        Rollback the last N migrations.

        Args:
            steps: Number of migrations to rollback (default: 1)
        """
        print("\n" + "=" * 60)
        print("ROLLING BACK MIGRATIONS")
        print("=" * 60 + "\n")

        migrations = self._get_migration_files()
        applied = self._get_applied_migrations()

        if not applied:
            print("[OK] No migrations to rollback")
            return

        # Get migrations to rollback (in reverse order)
        migrations_dict = dict(migrations)
        to_rollback = applied[-steps:][::-1]

        print(f"Rolling back {len(to_rollback)} migration(s):\n")
        for rev in to_rollback:
            print(f"  • {rev}")
        print()

        # Confirm
        confirm = input("Are you sure you want to rollback? (yes/no): ")
        if confirm.lower() != "yes":
            print("Rollback cancelled")
            return

        # Rollback migrations
        for revision in to_rollback:
            print(f"Rolling back {revision}...")

            try:
                file_path = migrations_dict.get(revision)
                if not file_path:
                    print(f"[ERROR] Migration file not found for {revision}")
                    continue

                module = self._load_migration_module(file_path)
                module.downgrade(self.engine)
                self._mark_migration_unapplied(revision)
                print(f"[OK] {revision} rolled back\n")

            except Exception as e:
                print(f"[ERROR] Failed to rollback {revision}: {str(e)}")
                raise

        print("=" * 60)
        print("[OK] Rollback completed successfully")
        print("=" * 60 + "\n")

    def status(self):
        """Show migration status."""
        print("\n" + "=" * 60)
        print("MIGRATION STATUS")
        print("=" * 60 + "\n")

        migrations = self._get_migration_files()
        applied = self._get_applied_migrations()

        if not migrations:
            print("No migrations found")
            return

        print(f"Total migrations: {len(migrations)}")
        print(f"Applied: {len(applied)}")
        print(f"Pending: {len(migrations) - len(applied)}\n")

        print("Migrations:\n")
        for revision, file_path in migrations:
            status = "[APPLIED]" if revision in applied else "[PENDING]"
            print(f"  {status}  {revision}")

            # Load module to get description
            try:
                module = self._load_migration_module(file_path)
                if hasattr(module, '__doc__') and module.__doc__:
                    desc = module.__doc__.strip().split('\n')[1].replace('Description:', '').strip()
                    print(f"           {desc}")
            except:
                pass

        print("\n" + "=" * 60 + "\n")

    def history(self):
        """Show migration history."""
        print("\n" + "=" * 60)
        print("MIGRATION HISTORY")
        print("=" * 60 + "\n")

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT revision, applied_at
                FROM migration_history
                ORDER BY applied_at
            """))

            rows = list(result)
            if not rows:
                print("No migrations applied yet")
                return

            print(f"Applied {len(rows)} migration(s):\n")
            for revision, applied_at in rows:
                print(f"  {revision}")
                print(f"    Applied: {applied_at}\n")

        print("=" * 60 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]
    manager = MigrationManager()

    if command == "upgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        manager.upgrade(target)

    elif command == "downgrade":
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        manager.downgrade(steps)

    elif command == "status":
        manager.status()

    elif command == "history":
        manager.history()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
