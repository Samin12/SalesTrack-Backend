"""
Migration script to add daily sync tables for YouTube data synchronization.
Run this script to create the necessary tables for the daily sync system.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.daily_sync import DailyYouTubeSync, YouTubeDataSnapshot, SyncConfiguration, SyncMetrics
from app.models.base import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_daily_sync_tables():
    """Create daily sync tables in the database."""
    try:
        # Create database engine
        engine = create_engine(settings.DATABASE_URL)
        
        logger.info("Creating daily sync tables...")
        
        # Create all tables defined in the models
        Base.metadata.create_all(bind=engine, tables=[
            DailyYouTubeSync.__table__,
            YouTubeDataSnapshot.__table__,
            SyncConfiguration.__table__,
            SyncMetrics.__table__
        ])
        
        logger.info("Daily sync tables created successfully!")
        
        # Create indexes for better performance
        with engine.connect() as conn:
            logger.info("Creating additional indexes...")
            
            # Index for sync status queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_daily_youtube_syncs_channel_status 
                ON daily_youtube_syncs(channel_id, sync_status);
            """))
            
            # Index for completed syncs ordered by completion time
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_daily_youtube_syncs_completed_at 
                ON daily_youtube_syncs(channel_id, completed_at DESC) 
                WHERE sync_status = 'completed';
            """))
            
            # Index for snapshot lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_youtube_data_snapshots_sync_channel 
                ON youtube_data_snapshots(sync_id, channel_id);
            """))
            
            # Index for sync metrics queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sync_metrics_channel_recorded 
                ON sync_metrics(channel_id, recorded_at DESC);
            """))
            
            conn.commit()
            logger.info("Indexes created successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating daily sync tables: {e}")
        return False


def create_default_sync_configuration():
    """Create default sync configuration for the main channel."""
    try:
        from app.database import get_db
        from app.core.config import get_youtube_config
        
        # Get database session
        db = next(get_db())
        
        # Get YouTube configuration
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id", "UCzGcYErpBX4ldvv0l7MWLfw")
        
        # Check if configuration already exists
        existing_config = db.query(SyncConfiguration).filter(
            SyncConfiguration.channel_id == channel_id
        ).first()
        
        if not existing_config:
            logger.info(f"Creating default sync configuration for channel {channel_id}")
            
            default_config = SyncConfiguration(
                channel_id=channel_id,
                sync_enabled=True,
                sync_frequency_hours=24,
                max_retries=3,
                retry_delay_minutes=30,
                daily_quota_limit=10000,
                quota_reset_hour=0,
                keep_snapshots_days=90,
                notify_on_failure=True
            )
            
            db.add(default_config)
            db.commit()
            
            logger.info("Default sync configuration created successfully!")
        else:
            logger.info("Sync configuration already exists, skipping creation")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"Error creating default sync configuration: {e}")
        return False


def main():
    """Main migration function."""
    logger.info("Starting daily sync tables migration...")
    
    # Create tables
    if not create_daily_sync_tables():
        logger.error("Failed to create daily sync tables")
        return False
    
    # Create default configuration
    if not create_default_sync_configuration():
        logger.error("Failed to create default sync configuration")
        return False
    
    logger.info("Daily sync migration completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
