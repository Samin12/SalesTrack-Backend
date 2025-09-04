"""
Database models for daily YouTube data synchronization.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.sql import func
from app.models.base import Base
import uuid


class DailyYouTubeSync(Base):
    """Daily YouTube synchronization tracking table."""
    __tablename__ = "daily_youtube_syncs"
    
    sync_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = Column(String(255), nullable=False, index=True)
    sync_status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed, cancelled
    started_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    videos_synced = Column(Integer, default=0)
    api_calls_made = Column(Integer, default=0)
    
    # Performance metrics
    sync_duration_seconds = Column(Float, nullable=True)
    data_size_bytes = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class YouTubeDataSnapshot(Base):
    """Daily snapshot of YouTube channel and video data."""
    __tablename__ = "youtube_data_snapshots"
    
    snapshot_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sync_id = Column(String(36), nullable=False, index=True)  # Foreign key to DailyYouTubeSync
    channel_id = Column(String(255), nullable=False, index=True)
    
    # Channel data
    channel_title = Column(String(500), nullable=False)
    subscriber_count = Column(Integer, nullable=False)
    view_count = Column(Integer, nullable=False)
    video_count = Column(Integer, nullable=False)
    
    # Video data (stored as JSON for flexibility)
    videos_data = Column(JSON, nullable=False)  # Array of video objects from YouTube API
    
    # Timestamps
    sync_timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Indexes for performance
    __table_args__ = (
        {'comment': 'Daily snapshots of YouTube channel and video data for analytics'}
    )


class SyncConfiguration(Base):
    """Configuration settings for daily sync operations."""
    __tablename__ = "sync_configurations"
    
    config_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = Column(String(255), nullable=False, unique=True, index=True)
    
    # Sync settings
    sync_enabled = Column(Boolean, default=True)
    sync_frequency_hours = Column(Integer, default=24)
    max_retries = Column(Integer, default=3)
    retry_delay_minutes = Column(Integer, default=30)
    
    # API quota management
    daily_quota_limit = Column(Integer, default=10000)  # YouTube API quota units per day
    quota_reset_hour = Column(Integer, default=0)  # Hour when quota resets (0-23)
    
    # Data retention
    keep_snapshots_days = Column(Integer, default=90)  # How long to keep historical snapshots
    
    # Notification settings
    notify_on_failure = Column(Boolean, default=True)
    notification_email = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class SyncMetrics(Base):
    """Performance and usage metrics for sync operations."""
    __tablename__ = "sync_metrics"
    
    metric_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sync_id = Column(String(36), nullable=False, index=True)
    channel_id = Column(String(255), nullable=False, index=True)
    
    # Performance metrics
    total_duration_seconds = Column(Float, nullable=False)
    api_calls_made = Column(Integer, nullable=False)
    videos_processed = Column(Integer, nullable=False)
    data_transferred_bytes = Column(Integer, nullable=False)
    
    # Success metrics
    videos_updated = Column(Integer, default=0)
    videos_added = Column(Integer, default=0)
    videos_removed = Column(Integer, default=0)
    
    # Error tracking
    api_errors = Column(Integer, default=0)
    rate_limit_hits = Column(Integer, default=0)
    timeout_errors = Column(Integer, default=0)
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), default=func.now())
