"""
Add Google Analytics 4 fields to UTM links table

This migration adds GA4 integration fields to track analytics data
from Google Analytics alongside direct click tracking.
"""

import sqlite3
import os
from datetime import datetime
from loguru import logger


def run_migration():
    """Add GA4 fields to utm_links table"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), "..", "youtube_analytics.db")
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if GA4 fields already exist
        cursor.execute("PRAGMA table_info(utm_links)")
        columns = [column[1] for column in cursor.fetchall()]
        
        ga4_fields = ['ga4_enabled', 'ga4_clicks', 'ga4_users', 'ga4_sessions', 'ga4_last_sync']
        missing_fields = [field for field in ga4_fields if field not in columns]
        
        if not missing_fields:
            logger.info("GA4 fields already exist in utm_links table")
            conn.close()
            return True
        
        logger.info(f"Adding GA4 fields to utm_links table: {missing_fields}")
        
        # Add GA4 fields
        migrations = [
            "ALTER TABLE utm_links ADD COLUMN ga4_enabled BOOLEAN DEFAULT 1 NOT NULL",
            "ALTER TABLE utm_links ADD COLUMN ga4_clicks INTEGER DEFAULT 0 NOT NULL", 
            "ALTER TABLE utm_links ADD COLUMN ga4_users INTEGER DEFAULT 0 NOT NULL",
            "ALTER TABLE utm_links ADD COLUMN ga4_sessions INTEGER DEFAULT 0 NOT NULL",
            "ALTER TABLE utm_links ADD COLUMN ga4_last_sync DATETIME"
        ]
        
        for migration in migrations:
            try:
                cursor.execute(migration)
                logger.info(f"Executed: {migration}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"Column already exists, skipping: {migration}")
                else:
                    raise e
        
        # Create index for GA4 sync queries
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_utm_ga4_sync ON utm_links(ga4_last_sync)")
            logger.info("Created GA4 sync index")
        except sqlite3.OperationalError as e:
            logger.warning(f"Index creation failed: {e}")
        
        conn.commit()
        logger.info("GA4 migration completed successfully")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(utm_links)")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"UTM links table now has columns: {columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"GA4 migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ GA4 migration completed successfully")
    else:
        print("❌ GA4 migration failed")
        exit(1)
