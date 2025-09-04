"""
Add PostHog analytics fields to UTM links table
Migration to support PostHog analytics integration
"""

import sqlite3
from datetime import datetime


def run_migration():
    """Add PostHog fields to utm_links table"""
    
    db_path = "./youtube_analytics.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Starting PostHog fields migration...")
        
        # Check if PostHog fields already exist
        cursor.execute("PRAGMA table_info(utm_links)")
        columns = [column[1] for column in cursor.fetchall()]
        
        posthog_fields = [
            'posthog_enabled',
            'posthog_events', 
            'posthog_users',
            'posthog_sessions',
            'posthog_last_sync'
        ]
        
        # Add PostHog fields if they don't exist
        for field in posthog_fields:
            if field not in columns:
                if field == 'posthog_enabled':
                    cursor.execute(f"ALTER TABLE utm_links ADD COLUMN {field} BOOLEAN DEFAULT 1 NOT NULL")
                elif field == 'posthog_last_sync':
                    cursor.execute(f"ALTER TABLE utm_links ADD COLUMN {field} DATETIME")
                else:
                    cursor.execute(f"ALTER TABLE utm_links ADD COLUMN {field} INTEGER DEFAULT 0 NOT NULL")
                print(f"Added column: {field}")
            else:
                print(f"Column {field} already exists, skipping")
        
        # Update tracking_type values from 'direct_ga4' to 'direct_posthog' for new links
        # (keeping existing GA4 links as-is for backward compatibility)
        cursor.execute("""
            UPDATE utm_links 
            SET posthog_enabled = 1, ga4_enabled = 0 
            WHERE created_at > datetime('now', '-1 day')
        """)
        
        # Commit changes
        conn.commit()
        print("PostHog fields migration completed successfully")

        # Show summary
        cursor.execute("SELECT COUNT(*) FROM utm_links WHERE posthog_enabled = 1")
        posthog_enabled_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM utm_links WHERE ga4_enabled = 1")
        ga4_enabled_count = cursor.fetchone()[0]

        print(f"Migration summary:")
        print(f"- Links with PostHog enabled: {posthog_enabled_count}")
        print(f"- Links with GA4 enabled: {ga4_enabled_count}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()
