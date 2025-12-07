"""
Migration script to add authentication fields to users table.

This script adds Google OAuth and role-based access control fields to the users table.

Usage:
    python src/migrations/add_auth_fields.py          # Apply migration
    python src/migrations/add_auth_fields.py --rollback  # Rollback migration
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.config.db import get_database_connection, initialize_database


def apply_migration():
    """Apply authentication fields migration."""
    print("=" * 60)
    print("Starting authentication fields migration...")
    print("=" * 60)
    
    # Initialize database
    db = initialize_database()
    
    if not db.test_connection():
        print("❌ Database connection failed!")
        return False
    
    print("✓ Database connection established")
    
    try:
        with db.get_session() as session:
            # Add Google OAuth fields
            print("\n1. Adding Google OAuth fields...")
            
            # Add google_id column
            try:
                session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE
                """))
                print("   ✓ Added google_id column")
            except Exception as e:
                print(f"   ℹ google_id column: {str(e)}")
            
            # Add picture_url column
            try:
                session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS picture_url VARCHAR(500)
                """))
                print("   ✓ Added picture_url column")
            except Exception as e:
                print(f"   ℹ picture_url column: {str(e)}")
            
            # Add role-based access control fields
            print("\n2. Adding role-based access control fields...")
            
            # Add role column with default value
            try:
                session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user' NOT NULL
                """))
                print("   ✓ Added role column")
            except Exception as e:
                print(f"   ℹ role column: {str(e)}")
            
            # Add is_verified column
            try:
                session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("   ✓ Added is_verified column")
            except Exception as e:
                print(f"   ℹ is_verified column: {str(e)}")
            
            # Add last_login column
            try:
                session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS last_login TIMESTAMP
                """))
                print("   ✓ Added last_login column")
            except Exception as e:
                print(f"   ℹ last_login column: {str(e)}")
            
            # Update email column to be NOT NULL
            print("\n3. Updating email column constraints...")
            try:
                session.execute(text("""
                    ALTER TABLE users 
                    ALTER COLUMN email SET NOT NULL
                """))
                print("   ✓ Updated email column to NOT NULL")
            except Exception as e:
                print(f"   ℹ email column: {str(e)}")
            
            # Create indexes
            print("\n4. Creating indexes...")
            
            try:
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id)
                """))
                print("   ✓ Created index on google_id")
            except Exception as e:
                print(f"   ℹ google_id index: {str(e)}")
            
            try:
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)
                """))
                print("   ✓ Created index on role")
            except Exception as e:
                print(f"   ℹ role index: {str(e)}")
            
            # Update existing users
            print("\n5. Updating existing users...")
            
            try:
                result = session.execute(text("""
                    UPDATE users 
                    SET role = 'user' 
                    WHERE role IS NULL OR role = ''
                """))
                print(f"   ✓ Updated {result.rowcount} users with default role")
            except Exception as e:
                print(f"   ℹ updating users: {str(e)}")
            
            # Commit happens automatically when exiting the context manager
            
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        
        # Display current table structure
        print("\nCurrent users table structure:")
        with db.get_session() as session:
            result = session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """))
            
            for row in result:
                print(f"  - {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def rollback_migration():
    """Rollback authentication fields migration."""
    print("=" * 60)
    print("Rolling back authentication fields migration...")
    print("=" * 60)
    
    db = initialize_database()
    
    if not db.test_connection():
        print("❌ Database connection failed!")
        return False
    
    print("✓ Database connection established")
    
    try:
        with db.get_session() as session:
            # Drop indexes
            print("\n1. Dropping indexes...")
            session.execute(text("DROP INDEX IF EXISTS ix_users_google_id"))
            session.execute(text("DROP INDEX IF EXISTS ix_users_role"))
            print("   ✓ Dropped indexes")
            
            # Drop columns
            print("\n2. Dropping authentication columns...")
            session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS google_id"))
            session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS picture_url"))
            session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS role"))
            session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS is_verified"))
            session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS last_login"))
            print("   ✓ Dropped columns")
            
            # Revert email column
            print("\n3. Reverting email column...")
            session.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
            print("   ✓ Reverted email column")
            
            # Commit happens automatically when exiting the context manager
        
        print("\n" + "=" * 60)
        print("✅ Rollback completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        success = rollback_migration()
    else:
        success = apply_migration()
    
    sys.exit(0 if success else 1)

