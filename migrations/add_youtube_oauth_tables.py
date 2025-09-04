#!/usr/bin/env python3
"""
Database migration to add YouTube OAuth and Analytics tables.
"""
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings


def create_youtube_oauth_tables():
    """Create YouTube OAuth and Analytics tables."""
    
    engine = create_engine(settings.DATABASE_URL)
    
    # SQL statements to create the tables
    youtube_oauth_tokens_table = """
    CREATE TABLE IF NOT EXISTS youtube_oauth_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id VARCHAR(255),
        channel_id VARCHAR(255) NOT NULL UNIQUE,
        access_token TEXT NOT NULL,
        refresh_token TEXT,
        token_type VARCHAR(50) DEFAULT 'Bearer',
        expires_at DATETIME,
        scope TEXT,
        is_active BOOLEAN DEFAULT 1,
        last_refreshed DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_error TEXT,
        error_count INTEGER DEFAULT 0
    );
    """
    
    youtube_analytics_data_table = """
    CREATE TABLE IF NOT EXISTS youtube_analytics_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id VARCHAR(255) NOT NULL,
        video_id VARCHAR(255),
        date DATETIME NOT NULL,
        granularity VARCHAR(20) DEFAULT 'day',
        views INTEGER DEFAULT 0,
        subscribers_gained INTEGER DEFAULT 0,
        subscribers_lost INTEGER DEFAULT 0,
        estimated_minutes_watched INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        dislikes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        average_view_duration_seconds INTEGER DEFAULT 0,
        average_view_percentage INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    youtube_traffic_sources_table = """
    CREATE TABLE IF NOT EXISTS youtube_traffic_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id VARCHAR(255) NOT NULL,
        video_id VARCHAR(255),
        date DATETIME NOT NULL,
        traffic_source_type VARCHAR(100) NOT NULL,
        traffic_source_detail VARCHAR(255),
        views INTEGER DEFAULT 0,
        estimated_minutes_watched INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create indexes for better performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_youtube_oauth_tokens_channel_id ON youtube_oauth_tokens(channel_id);",
        "CREATE INDEX IF NOT EXISTS idx_youtube_oauth_tokens_is_active ON youtube_oauth_tokens(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_youtube_analytics_data_channel_id ON youtube_analytics_data(channel_id);",
        "CREATE INDEX IF NOT EXISTS idx_youtube_analytics_data_video_id ON youtube_analytics_data(video_id);",
        "CREATE INDEX IF NOT EXISTS idx_youtube_analytics_data_date ON youtube_analytics_data(date);",
        "CREATE INDEX IF NOT EXISTS idx_youtube_traffic_sources_channel_id ON youtube_traffic_sources(channel_id);",
        "CREATE INDEX IF NOT EXISTS idx_youtube_traffic_sources_date ON youtube_traffic_sources(date);",
    ]
    
    try:
        with engine.connect() as connection:
            # Create tables
            print("Creating youtube_oauth_tokens table...")
            connection.execute(text(youtube_oauth_tokens_table))
            
            print("Creating youtube_analytics_data table...")
            connection.execute(text(youtube_analytics_data_table))
            
            print("Creating youtube_traffic_sources table...")
            connection.execute(text(youtube_traffic_sources_table))
            
            # Create indexes
            print("Creating indexes...")
            for index_sql in indexes:
                connection.execute(text(index_sql))
            
            connection.commit()
            print("✅ Successfully created YouTube OAuth and Analytics tables!")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise


def rollback_youtube_oauth_tables():
    """Rollback YouTube OAuth and Analytics tables."""
    
    engine = create_engine(settings.DATABASE_URL)
    
    rollback_statements = [
        "DROP TABLE IF EXISTS youtube_traffic_sources;",
        "DROP TABLE IF EXISTS youtube_analytics_data;",
        "DROP TABLE IF EXISTS youtube_oauth_tokens;",
    ]
    
    try:
        with engine.connect() as connection:
            for statement in rollback_statements:
                print(f"Executing: {statement}")
                connection.execute(text(statement))
            
            connection.commit()
            print("✅ Successfully rolled back YouTube OAuth and Analytics tables!")
            
    except Exception as e:
        print(f"❌ Error rolling back tables: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube OAuth and Analytics tables migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    
    args = parser.parse_args()
    
    if args.rollback:
        print("🔄 Rolling back YouTube OAuth and Analytics tables...")
        rollback_youtube_oauth_tables()
    else:
        print("🚀 Creating YouTube OAuth and Analytics tables...")
        create_youtube_oauth_tables()
    
    print("Migration completed!")
