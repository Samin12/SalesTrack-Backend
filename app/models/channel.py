"""
Channel model for storing YouTube channel information and metrics.
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Channel(BaseModel):
    """YouTube channel model."""
    __tablename__ = "channels"
    
    # Channel identification
    channel_id = Column(String(50), unique=True, index=True, nullable=False)
    channel_handle = Column(String(100), unique=True, index=True)
    channel_name = Column(String(200), nullable=False)
    channel_description = Column(Text)
    
    # Channel metadata
    custom_url = Column(String(200))
    published_at = Column(DateTime(timezone=True))
    country = Column(String(10))
    default_language = Column(String(10))
    
    # Current metrics
    subscriber_count = Column(BigInteger, default=0)
    video_count = Column(Integer, default=0)
    view_count = Column(BigInteger, default=0)
    
    # Channel status
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True))
    
    # Relationships
    videos = relationship("Video", back_populates="channel")
    channel_metrics = relationship("ChannelMetrics", back_populates="channel")
    
    def __repr__(self):
        return f"<Channel(id={self.id}, handle={self.channel_handle}, name={self.channel_name})>"


class ChannelMetrics(BaseModel):
    """Historical channel metrics for tracking growth over time."""
    __tablename__ = "channel_metrics"
    
    # Foreign key to channel
    channel_id = Column(String(50), ForeignKey("channels.channel_id"), nullable=False, index=True)
    
    # Metrics snapshot date
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Core metrics
    subscriber_count = Column(BigInteger, default=0)
    video_count = Column(Integer, default=0)
    view_count = Column(BigInteger, default=0)
    
    # Growth calculations
    subscriber_growth = Column(Integer, default=0)  # Change from previous period
    subscriber_growth_rate = Column(Float, default=0.0)  # Percentage growth
    view_growth = Column(BigInteger, default=0)  # Change from previous period
    view_growth_rate = Column(Float, default=0.0)  # Percentage growth
    
    # Additional metrics
    estimated_minutes_watched = Column(BigInteger, default=0)
    average_view_duration = Column(Float, default=0.0)
    
    # Data source
    data_source = Column(String(50), default="youtube_api")  # youtube_api, scrapecreators, etc.
    
    # Relationships
    channel = relationship("Channel", back_populates="channel_metrics")
    
    def __repr__(self):
        return f"<ChannelMetrics(channel_id={self.channel_id}, date={self.date}, subscribers={self.subscriber_count})>"
