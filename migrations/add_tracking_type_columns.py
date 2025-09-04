"""
Add tracking type columns to UTM links table

This migration adds support for dual tracking methods:
1. server_redirect: Traditional redirect through our server (current behavior)
2. direct_ga4: Direct UTM links that bypass our server for better UX

Adds:
- tracking_type: ENUM to specify tracking method
- direct_url: TEXT to store the final URL with UTM parameters
"""

import sqlite3
import os
from datetime import datetime
from loguru import logger


def generate_direct_url(destination_url, utm_source, utm_medium, utm_campaign, utm_content=None, utm_term=None):
    """Generate direct URL with UTM parameters"""
    params = []
    
    if utm_source:
        params.append(f"utm_source={utm_source}")
    if utm_medium:
        params.append(f"utm_medium={utm_medium}")
    if utm_campaign:
        params.append(f"utm_campaign={utm_campaign}")
    if utm_content:
        params.append(f"utm_content={utm_content}")
    if utm_term:
        params.append(f"utm_term={utm_term}")
    
    separator = "&" if "?" in destination_url else "?"
    return f"{destination_url}{separator}{'&'.join(params)}"


def run_migration():
    """Add tracking type columns to utm_links table"""
    
    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), "..", "youtube_analytics.db")
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(utm_links)")
        columns = [column[1] for column in cursor.fetchall()]
        
        missing_fields = []
        if "tracking_type" not in columns:
            missing_fields.append("tracking_type")
        if "direct_url" not in columns:
            missing_fields.append("direct_url")
        
        if not missing_fields:
            logger.info("Tracking type columns already exist")
            conn.close()
            return True
        
        logger.info(f"Adding tracking type columns: {missing_fields}")
        
        # Add tracking type columns
        migrations = []
        
        if "tracking_type" in missing_fields:
            migrations.append("ALTER TABLE utm_links ADD COLUMN tracking_type TEXT DEFAULT 'server_redirect' NOT NULL")
        
        if "direct_url" in missing_fields:
            migrations.append("ALTER TABLE utm_links ADD COLUMN direct_url TEXT")
        
        for migration in migrations:
            try:
                cursor.execute(migration)
                logger.info(f"Executed: {migration}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"Column already exists, skipping: {migration}")
                else:
                    raise e
        
        # Populate direct_url for existing records
        if "direct_url" in missing_fields:
            logger.info("Populating direct_url for existing records...")
            
            cursor.execute("""
                SELECT id, destination_url, utm_source, utm_medium, utm_campaign, utm_content, utm_term
                FROM utm_links 
                WHERE direct_url IS NULL
            """)
            
            records = cursor.fetchall()
            logger.info(f"Found {len(records)} records to update")
            
            for record in records:
                link_id, dest_url, source, medium, campaign, content, term = record
                
                # Generate direct URL
                direct_url = generate_direct_url(dest_url, source, medium, campaign, content, term)
                
                cursor.execute("""
                    UPDATE utm_links 
                    SET direct_url = ? 
                    WHERE id = ?
                """, (direct_url, link_id))
            
            logger.info(f"Updated {len(records)} records with direct URLs")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info("✅ Tracking type migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
