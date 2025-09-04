"""
Video model for storing YouTube video information and metrics.
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Video(BaseModel):
    """YouTube video model."""
    __tablename__ = "videos"
    
    # Video identification
    video_id = Column(String(50), unique=True, index=True, nullable=False)
    channel_id = Column(String(50), ForeignKey("channels.channel_id"), nullable=False, index=True)
    
    # Video metadata
    title = Column(String(500), nullable=False)
    description = Column(Text)
    published_at = Column(DateTime(timezone=True), nullable=False)
    duration = Column(String(20))  # ISO 8601 duration format
    duration_seconds = Column(Integer)  # Duration in seconds for calculations
    
    # Video properties
    category_id = Column(String(10))
    default_language = Column(String(10))
    default_audio_language = Column(String(10))
    
    # Privacy and status
    privacy_status = Column(String(20))  # public, unlisted, private
    upload_status = Column(String(20))   # uploaded, processed, failed
    license = Column(String(50))         # youtube, creativeCommon
    
    # Current metrics
    view_count = Column(BigInteger, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    
    # Video tags and thumbnails
    tags = Column(Text)  # JSON string of tags
    thumbnail_url = Column(String(500))
    
    # Status
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True))
    
    # Relationships
    channel = relationship("Channel", back_populates="videos")
    video_metrics = relationship("VideoMetrics", back_populates="video")
    weekly_metrics = relationship("WeeklyVideoMetrics", back_populates="video", cascade="all, delete-orphan")
    # Note: UTM links relationship removed to allow tracking new videos without FK constraint
    
    def __repr__(self):
        return f"<Video(id={self.id}, video_id={self.video_id}, title={self.title[:50]}...)>"


class VideoMetrics(BaseModel):
    """Historical video metrics for tracking performance over time."""
    __tablename__ = "video_metrics"
    
    # Foreign key to video
    video_id = Column(String(50), ForeignKey("videos.video_id"), nullable=False, index=True)
    
    # Metrics snapshot date
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Core metrics
    view_count = Column(BigInteger, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    
    # Growth calculations
    view_growth = Column(BigInteger, default=0)  # Change from previous period
    view_growth_rate = Column(Float, default=0.0)  # Percentage growth
    like_growth = Column(Integer, default=0)  # Change from previous period
    comment_growth = Column(Integer, default=0)  # Change from previous period
    
    # Engagement metrics
    like_rate = Column(Float, default=0.0)  # Likes per view
    comment_rate = Column(Float, default=0.0)  # Comments per view
    engagement_rate = Column(Float, default=0.0)  # Overall engagement
    
    # Performance metrics
    estimated_minutes_watched = Column(BigInteger, default=0)
    average_view_duration = Column(Float, default=0.0)
    average_view_percentage = Column(Float, default=0.0)
    
    # Traffic sources (if available)
    traffic_source_youtube_search = Column(Float, default=0.0)
    traffic_source_suggested_videos = Column(Float, default=0.0)
    traffic_source_external = Column(Float, default=0.0)
    traffic_source_direct = Column(Float, default=0.0)
    
    # Data source
    data_source = Column(String(50), default="youtube_api")
    
    # Relationships
    video = relationship("Video", back_populates="video_metrics")
    
    def __repr__(self):
        return f"<VideoMetrics(video_id={self.video_id}, date={self.date}, views={self.view_count})>"
