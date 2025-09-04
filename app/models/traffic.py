"""
Traffic and conversion tracking models.
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, DateTime, Text, Boolean
from app.models.base import BaseModel


class WebsiteTraffic(BaseModel):
    """Website traffic from YouTube sources."""
    __tablename__ = "website_traffic"
    
    # Date and source tracking
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(100), nullable=False)  # youtube_channel, youtube_video, youtube_description
    source_id = Column(String(100))  # video_id or channel_id if applicable
    
    # Traffic metrics
    clicks = Column(Integer, default=0)
    unique_clicks = Column(Integer, default=0)
    click_through_rate = Column(Float, default=0.0)
    
    # Conversion tracking
    page_views = Column(Integer, default=0)
    unique_page_views = Column(Integer, default=0)
    bounce_rate = Column(Float, default=0.0)
    average_session_duration = Column(Float, default=0.0)
    
    # Geographic data
    country = Column(String(10))
    region = Column(String(100))
    
    # Device and platform
    device_type = Column(String(50))  # desktop, mobile, tablet
    platform = Column(String(50))    # windows, mac, android, ios
    
    # Referrer information
    referrer_url = Column(String(500))
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    
    # Data source
    data_source = Column(String(50), default="analytics")
    
    def __repr__(self):
        return f"<WebsiteTraffic(date={self.date}, source={self.source}, clicks={self.clicks})>"


class ConversionEvent(BaseModel):
    """Conversion events from YouTube traffic."""
    __tablename__ = "conversion_events"
    
    # Event tracking
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # signup, purchase, download, etc.
    event_value = Column(Float, default=0.0)  # Monetary value if applicable
    
    # Source tracking
    youtube_source = Column(String(100))  # channel, video, description, etc.
    youtube_source_id = Column(String(100))  # video_id or channel_id
    
    # User tracking (anonymized)
    user_id = Column(String(100))  # Anonymized user identifier
    session_id = Column(String(100))  # Session identifier
    
    # Conversion funnel
    funnel_step = Column(String(100))  # awareness, consideration, conversion
    time_to_conversion = Column(Integer)  # Minutes from first YouTube interaction
    
    # Additional data
    conversion_data = Column(Text)  # JSON string for additional event data
    
    # Data source
    data_source = Column(String(50), default="analytics")
    
    def __repr__(self):
        return f"<ConversionEvent(date={self.date}, type={self.event_type}, value={self.event_value})>"


class YouTubeAnalytics(BaseModel):
    """YouTube Analytics API data storage."""
    __tablename__ = "youtube_analytics"
    
    # Date and dimensions
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    channel_id = Column(String(50), nullable=False, index=True)
    video_id = Column(String(50), index=True)  # Optional, for video-specific analytics
    
    # Metrics
    views = Column(BigInteger, default=0)
    watch_time_minutes = Column(BigInteger, default=0)
    average_view_duration = Column(Float, default=0.0)
    subscriber_gained = Column(Integer, default=0)
    subscriber_lost = Column(Integer, default=0)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # Revenue metrics (if monetized)
    estimated_revenue = Column(Float, default=0.0)
    estimated_ad_revenue = Column(Float, default=0.0)
    estimated_red_revenue = Column(Float, default=0.0)
    
    # Traffic sources
    traffic_source_type = Column(String(100))  # SEARCH, SUGGESTED_VIDEO, etc.
    traffic_source_detail = Column(String(200))
    
    # Demographics
    viewer_percentage_male = Column(Float, default=0.0)
    viewer_percentage_female = Column(Float, default=0.0)
    top_age_group = Column(String(20))
    top_geography = Column(String(10))
    
    # Device and platform
    device_type = Column(String(50))
    operating_system = Column(String(50))
    
    # Data source and quality
    data_source = Column(String(50), default="youtube_analytics_api")
    is_estimated = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<YouTubeAnalytics(date={self.date}, channel_id={self.channel_id}, views={self.views})>"
