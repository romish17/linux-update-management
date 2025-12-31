#!/usr/bin/env python3
"""
Migration script to update database schema
Adds new columns to update_history table and creates scheduled_updates table
"""
import sqlite3
import os
import sys

def find_database():
    """Find the database file"""
    possible_locations = [
        'updates.db',
        'instance/updates.db',
        '/root/linux-update-management/updates.db',
        '/root/linux-update-management/instance/updates.db'
    ]

    for location in possible_locations:
        if os.path.exists(location):
            return location

    return None

def migrate_database(db_path=None):
    print("🔧 Starting database migration...")

    if db_path is None:
        db_path = find_database()

    if db_path is None:
        print("❌ Database not found in common locations.")
        print("ℹ️  Searching for database files...")
        # Try to find any .db file
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.db'):
                    found_path = os.path.join(root, file)
                    print(f"   Found: {found_path}")
                    use_it = input(f"   Use this database? (y/n): ").lower()
                    if use_it == 'y':
                        db_path = found_path
                        break
            if db_path:
                break

    if db_path is None:
        print("❌ No database found. Please ensure the app has been started at least once.")
        print("ℹ️  Run 'python app.py' to create the initial database, then run this migration script.")
        return False

    print(f"📁 Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if update_history table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='update_history'"
        )
        if not cursor.fetchone():
            print("⚠️  update_history table doesn't exist yet.")
            print("ℹ️  The database will be created automatically when you start the app.")
            return True

        # Check existing columns
        cursor.execute("PRAGMA table_info(update_history)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"   Current columns: {', '.join(columns)}")

        migrations_needed = []

        # Add server_hostname column if missing
        if 'server_hostname' not in columns:
            migrations_needed.append(
                ("server_hostname", "ALTER TABLE update_history ADD COLUMN server_hostname VARCHAR(255)")
            )

        # Add update_type column if missing
        if 'update_type' not in columns:
            migrations_needed.append(
                ("update_type", "ALTER TABLE update_history ADD COLUMN update_type VARCHAR(50) DEFAULT 'all'")
            )

        # Add package_list column if missing
        if 'package_list' not in columns:
            migrations_needed.append(
                ("package_list", "ALTER TABLE update_history ADD COLUMN package_list TEXT")
            )

        # Add duration column if missing
        if 'duration' not in columns:
            migrations_needed.append(
                ("duration", "ALTER TABLE update_history ADD COLUMN duration FLOAT")
            )

        # Execute migrations for update_history
        for col_name, migration in migrations_needed:
            print(f"  → Adding column: {col_name}")
            cursor.execute(migration)

        if migrations_needed:
            print(f"✓ Added {len(migrations_needed)} column(s) to update_history table")
        else:
            print("✓ update_history table is already up to date")

        # Check if scheduled_updates table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scheduled_updates'"
        )
        if not cursor.fetchone():
            print("  → Creating scheduled_updates table...")
            cursor.execute("""
                CREATE TABLE scheduled_updates (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    schedule_type VARCHAR(20) NOT NULL,
                    day_of_week INTEGER,
                    day_of_month INTEGER,
                    hour INTEGER NOT NULL,
                    minute INTEGER DEFAULT 0,
                    update_type VARCHAR(20) DEFAULT 'all',
                    auto_reboot BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(server_id) REFERENCES servers (id)
                )
            """)
            print("✓ Created scheduled_updates table")
        else:
            print("✓ scheduled_updates table already exists")

        # Commit changes
        conn.commit()
        print("✅ Database migration completed successfully!")
        print("\nℹ️  You can now restart your application.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    # Allow passing database path as argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)

