"""
Weekly metrics model for tracking video performance over time.
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WeeklyVideoMetrics(BaseModel):
    """Weekly video metrics for tracking performance over time."""
    __tablename__ = "weekly_video_metrics"
    
    # Foreign keys
    video_id = Column(String(50), ForeignKey("videos.video_id"), nullable=False)
    channel_id = Column(String(50), ForeignKey("channels.channel_id"), nullable=False)
    
    # Week identifier (e.g., "2025-W35" for week 35 of 2025)
    week_id = Column(String(10), nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    
    # Video metrics for this week
    view_count_start = Column(BigInteger, default=0)  # Views at start of week
    view_count_end = Column(BigInteger, default=0)    # Views at end of week
    views_gained = Column(BigInteger, default=0)      # Views gained this week
    
    like_count_start = Column(Integer, default=0)
    like_count_end = Column(Integer, default=0)
    likes_gained = Column(Integer, default=0)
    
    comment_count_start = Column(Integer, default=0)
    comment_count_end = Column(Integer, default=0)
    comments_gained = Column(Integer, default=0)
    
    # Website traffic metrics
    website_clicks = Column(Integer, default=0)
    website_page_views = Column(Integer, default=0)
    click_through_rate = Column(Float, default=0.0)
    
    # Growth rates
    view_growth_rate = Column(Float, default=0.0)     # Percentage growth
    engagement_growth_rate = Column(Float, default=0.0)
    
    # Rankings and performance
    rank_by_views = Column(Integer, default=0)        # Rank among all videos this week
    rank_by_growth = Column(Integer, default=0)       # Rank by growth rate
    
    # Data source and quality
    data_source = Column(String(50), default="youtube_scraper")
    data_quality_score = Column(Float, default=1.0)   # 0.0 to 1.0
    
    # Relationships
    video = relationship("Video", back_populates="weekly_metrics")
    channel = relationship("Channel")
    
    def __repr__(self):
        return f"<WeeklyVideoMetrics(video_id={self.video_id}, week={self.week_id}, views_gained={self.views_gained})>"


class WeeklyChannelSummary(BaseModel):
    """Weekly channel summary metrics."""
    __tablename__ = "weekly_channel_summary"
    
    # Foreign key
    channel_id = Column(String(50), ForeignKey("channels.channel_id"), nullable=False)
    
    # Week identifier
    week_id = Column(String(10), nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    
    # Aggregate metrics for the week
    total_views_gained = Column(BigInteger, default=0)
    total_likes_gained = Column(Integer, default=0)
    total_comments_gained = Column(Integer, default=0)
    total_website_clicks = Column(Integer, default=0)
    total_website_page_views = Column(Integer, default=0)
    
    # Channel-level metrics
    subscriber_count_start = Column(Integer, default=0)
    subscriber_count_end = Column(Integer, default=0)
    subscribers_gained = Column(Integer, default=0)
    subscriber_growth_rate = Column(Float, default=0.0)
    
    # Video activity
    videos_published = Column(Integer, default=0)
    active_videos_count = Column(Integer, default=0)  # Videos that gained views
    
    # Performance metrics
    average_views_per_video = Column(Float, default=0.0)
    top_video_id = Column(String(50))  # Best performing video this week
    top_video_views_gained = Column(BigInteger, default=0)
    
    # Engagement metrics
    total_engagement_rate = Column(Float, default=0.0)
    average_ctr = Column(Float, default=0.0)  # Click-through rate to website
    
    # Data quality
    data_completeness = Column(Float, default=1.0)  # Percentage of expected data collected
    
    # Relationships
    channel = relationship("Channel")
    
    def __repr__(self):
        return f"<WeeklyChannelSummary(channel_id={self.channel_id}, week={self.week_id}, views_gained={self.total_views_gained})>"


class VideoPerformanceSnapshot(BaseModel):
    """Snapshot of video performance at a specific point in time."""
    __tablename__ = "video_performance_snapshots"
    
    # Foreign key
    video_id = Column(String(50), ForeignKey("videos.video_id"), nullable=False)
    channel_id = Column(String(50), ForeignKey("channels.channel_id"), nullable=False)
    
    # Snapshot metadata
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    snapshot_type = Column(String(20), default="daily")  # daily, weekly, monthly
    
    # Performance metrics at this point in time
    view_count = Column(BigInteger, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    # Derived metrics
    engagement_rate = Column(Float, default=0.0)
    views_per_day_since_publish = Column(Float, default=0.0)
    
    # Ranking information
    rank_in_channel = Column(Integer, default=0)  # Rank among channel's videos
    percentile_performance = Column(Float, default=0.0)  # 0-100 percentile
    
    # External metrics (if available)
    estimated_revenue = Column(Float, default=0.0)
    estimated_cpm = Column(Float, default=0.0)
    
    # Relationships
    video = relationship("Video")
    channel = relationship("Channel")
    
    def __repr__(self):
        return f"<VideoPerformanceSnapshot(video_id={self.video_id}, date={self.snapshot_date}, views={self.view_count})>"
