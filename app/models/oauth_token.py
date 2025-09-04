"""
OAuth token storage models for YouTube Analytics API.
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from app.core.database import Base


class YouTubeOAuthToken(Base):
    """Store YouTube OAuth tokens for Analytics API access."""
    
    __tablename__ = "youtube_oauth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True)  # For multi-user support later
    channel_id = Column(String, nullable=False, unique=True)  # YouTube channel ID
    
    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String, default="Bearer")
    
    # Token metadata
    expires_at = Column(DateTime, nullable=True)
    scope = Column(Text, nullable=True)  # Granted scopes
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    last_refreshed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<YouTubeOAuthToken(channel_id='{self.channel_id}', is_active={self.is_active})>"
    
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at
    
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (expires within 5 minutes)."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))


class YouTubeAnalyticsData(Base):
    """Store historical YouTube analytics data."""
    
    __tablename__ = "youtube_analytics_data"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    video_id = Column(String, nullable=True, index=True)  # Null for channel-level data
    
    # Date and granularity
    date = Column(DateTime, nullable=False, index=True)
    granularity = Column(String, nullable=False, default="day")  # day, week, month
    
    # Core metrics
    views = Column(Integer, default=0)
    subscribers_gained = Column(Integer, default=0)
    subscribers_lost = Column(Integer, default=0)
    estimated_minutes_watched = Column(Integer, default=0)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # Advanced metrics
    average_view_duration_seconds = Column(Integer, default=0)
    average_view_percentage = Column(Integer, default=0)  # Percentage of video watched
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<YouTubeAnalyticsData(channel_id='{self.channel_id}', date='{self.date}', views={self.views})>"


class YouTubeTrafficSource(Base):
    """Store YouTube traffic source analytics."""
    
    __tablename__ = "youtube_traffic_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, nullable=False, index=True)
    video_id = Column(String, nullable=True, index=True)
    
    # Date range
    date = Column(DateTime, nullable=False, index=True)
    
    # Traffic source details
    traffic_source_type = Column(String, nullable=False)  # YT_SEARCH, SUGGESTED_VIDEO, etc.
    traffic_source_detail = Column(String, nullable=True)  # Specific source details
    
    # Metrics
    views = Column(Integer, default=0)
    estimated_minutes_watched = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<YouTubeTrafficSource(channel_id='{self.channel_id}', source='{self.traffic_source_type}', views={self.views})>"
