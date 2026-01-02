#!/usr/bin/env python3
"""
Database migration script to add CVE-related columns
Adds security and CVE tracking to servers and update_history tables
"""

from app import app, db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add CVE-related columns to existing tables"""
    with app.app_context():
        logger.info("Starting database migration for CVE support...")

        try:
            # Add columns to servers table
            logger.info("Adding columns to servers table...")
            with db.engine.connect() as conn:
                # Check if columns exist before adding
                result = conn.execute(db.text("PRAGMA table_info(servers)"))
                existing_columns = [row[1] for row in result]

                if 'security_updates_count' not in existing_columns:
                    conn.execute(db.text("ALTER TABLE servers ADD COLUMN security_updates_count INTEGER DEFAULT 0"))
                    conn.commit()
                    logger.info("✓ Added security_updates_count to servers")
                else:
                    logger.info("✓ security_updates_count already exists in servers")

                if 'critical_cves_count' not in existing_columns:
                    conn.execute(db.text("ALTER TABLE servers ADD COLUMN critical_cves_count INTEGER DEFAULT 0"))
                    conn.commit()
                    logger.info("✓ Added critical_cves_count to servers")
                else:
                    logger.info("✓ critical_cves_count already exists in servers")

            # Add columns to update_history table
            logger.info("Adding columns to update_history table...")
            with db.engine.connect() as conn:
                result = conn.execute(db.text("PRAGMA table_info(update_history)"))
                existing_columns = [row[1] for row in result]

                if 'security_count' not in existing_columns:
                    conn.execute(db.text("ALTER TABLE update_history ADD COLUMN security_count INTEGER DEFAULT 0"))
                    conn.commit()
                    logger.info("✓ Added security_count to update_history")
                else:
                    logger.info("✓ security_count already exists in update_history")

                if 'cve_list' not in existing_columns:
                    conn.execute(db.text("ALTER TABLE update_history ADD COLUMN cve_list TEXT"))
                    conn.commit()
                    logger.info("✓ Added cve_list to update_history")
                else:
                    logger.info("✓ cve_list already exists in update_history")

                if 'critical_cves' not in existing_columns:
                    conn.execute(db.text("ALTER TABLE update_history ADD COLUMN critical_cves TEXT"))
                    conn.commit()
                    logger.info("✓ Added critical_cves to update_history")
                else:
                    logger.info("✓ critical_cves already exists in update_history")

            logger.info("✅ Database migration completed successfully!")

        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == '__main__':
    migrate_database()
