#!/usr/bin/env python3
"""
Database migration to add UTM tracking tables for video-driven traffic analytics.
"""
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings


def create_utm_tracking_tables():
    """Create UTM tracking tables for video-driven traffic analytics."""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL statements to create the tables
    utm_links_table = """
    CREATE TABLE IF NOT EXISTS utm_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id VARCHAR(255) NOT NULL,
        destination_url TEXT NOT NULL,
        utm_source VARCHAR(100) NOT NULL DEFAULT 'youtube',
        utm_medium VARCHAR(100) NOT NULL DEFAULT 'video',
        utm_campaign VARCHAR(255) NOT NULL,
        utm_content VARCHAR(255),
        utm_term VARCHAR(255),
        tracking_url TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (video_id) REFERENCES videos (video_id)
    );
    """
    
    link_clicks_table = """
    CREATE TABLE IF NOT EXISTS link_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utm_link_id INTEGER NOT NULL,
        clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_agent TEXT,
        ip_address VARCHAR(45),
        referrer TEXT,
        country VARCHAR(2),
        device_type VARCHAR(50),
        browser VARCHAR(100),
        FOREIGN KEY (utm_link_id) REFERENCES utm_links (id) ON DELETE CASCADE
    );
    """
    
    # Create indexes for performance
    utm_links_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_utm_video_active ON utm_links (video_id, is_active);",
        "CREATE INDEX IF NOT EXISTS idx_utm_created ON utm_links (created_at);",
        "CREATE INDEX IF NOT EXISTS idx_utm_video_id ON utm_links (video_id);"
    ]
    
    link_clicks_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_click_link_date ON link_clicks (utm_link_id, clicked_at);",
        "CREATE INDEX IF NOT EXISTS idx_click_date ON link_clicks (clicked_at);",
        "CREATE INDEX IF NOT EXISTS idx_click_country ON link_clicks (country);",
        "CREATE INDEX IF NOT EXISTS idx_click_utm_link ON link_clicks (utm_link_id);"
    ]
    
    try:
        with engine.connect() as connection:
            print("🚀 Creating UTM tracking tables...")
            
            # Create tables
            print("📊 Creating utm_links table...")
            connection.execute(text(utm_links_table))
            
            print("📊 Creating link_clicks table...")
            connection.execute(text(link_clicks_table))
            
            # Create indexes
            print("🔍 Creating indexes for utm_links...")
            for index_sql in utm_links_indexes:
                connection.execute(text(index_sql))
            
            print("🔍 Creating indexes for link_clicks...")
            for index_sql in link_clicks_indexes:
                connection.execute(text(index_sql))
            
            # Commit the transaction
            connection.commit()
            
            print("✅ UTM tracking tables created successfully!")
            print("📈 Tables created:")
            print("   - utm_links (for tracking link generation)")
            print("   - link_clicks (for click event recording)")
            print("🔍 Indexes created for optimal query performance")
            
    except Exception as e:
        print(f"❌ Error creating UTM tracking tables: {str(e)}")
        return False
    
    return True


def verify_tables():
    """Verify that the UTM tracking tables were created successfully."""
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            print("\n🔍 Verifying table creation...")
            
            # Check utm_links table
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='utm_links';"))
            if result.fetchone():
                print("✅ utm_links table exists")
            else:
                print("❌ utm_links table not found")
                return False
            
            # Check link_clicks table
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='link_clicks';"))
            if result.fetchone():
                print("✅ link_clicks table exists")
            else:
                print("❌ link_clicks table not found")
                return False
            
            # Check table structure
            print("\n📋 Table structures:")
            
            # utm_links structure
            result = connection.execute(text("PRAGMA table_info(utm_links);"))
            utm_links_columns = result.fetchall()
            print(f"   utm_links: {len(utm_links_columns)} columns")
            for col in utm_links_columns:
                print(f"     - {col[1]} ({col[2]})")
            
            # link_clicks structure
            result = connection.execute(text("PRAGMA table_info(link_clicks);"))
            link_clicks_columns = result.fetchall()
            print(f"   link_clicks: {len(link_clicks_columns)} columns")
            for col in link_clicks_columns:
                print(f"     - {col[1]} ({col[2]})")
            
            print("\n✅ All UTM tracking tables verified successfully!")
            
    except Exception as e:
        print(f"❌ Error verifying tables: {str(e)}")
        return False
    
    return True


def main():
    """Main migration function."""
    print("🔄 UTM Tracking Tables Migration")
    print("=" * 50)
    print(f"📅 Migration started at: {datetime.now()}")
    print(f"🗄️  Database: {settings.DATABASE_URL}")
    print()
    
    # Create tables
    if not create_utm_tracking_tables():
        print("\n❌ Migration failed!")
        sys.exit(1)
    
    # Verify tables
    if not verify_tables():
        print("\n❌ Table verification failed!")
        sys.exit(1)
    
    print(f"\n🎉 Migration completed successfully at: {datetime.now()}")
    print("\n📊 UTM Tracking System Ready!")
    print("🔗 You can now:")
    print("   1. Create UTM tracking links for your YouTube videos")
    print("   2. Track clicks and user engagement")
    print("   3. Analyze video-driven traffic performance")
    print("   4. Generate correlation reports between views and clicks")


if __name__ == "__main__":
    main()
