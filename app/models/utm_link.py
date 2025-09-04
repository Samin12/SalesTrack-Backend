"""
UTM Link tracking models for video-driven traffic analytics.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class UTMLink(Base):
    """UTM tracking links associated with YouTube videos."""
    __tablename__ = "utm_links"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(255), nullable=False, index=True)  # No FK constraint to allow new videos
    destination_url = Column(Text, nullable=False)
    utm_source = Column(String(100), default="youtube", nullable=False)
    utm_medium = Column(String(100), default="video", nullable=False)
    utm_campaign = Column(String(255), nullable=False)  # Usually video_id
    utm_content = Column(String(255), nullable=True)  # Optional additional content
    utm_term = Column(String(255), nullable=True)  # Optional search terms
    
    # Generated tracking URL
    tracking_url = Column(Text, nullable=False)
    pretty_slug = Column(String(100), unique=True, nullable=True)  # Pretty URL slug

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive

    # Tracking Method Configuration
    tracking_type = Column(String(20), default="server_redirect", nullable=False)  # 'server_redirect' or 'direct_posthog'
    direct_url = Column(Text, nullable=True)  # Direct URL with UTM parameters for PostHog-only tracking

    # PostHog Analytics Integration
    posthog_enabled = Column(Boolean, default=True, nullable=False)  # Enable PostHog tracking
    posthog_events = Column(Integer, default=0, nullable=False)  # PostHog event count
    posthog_users = Column(Integer, default=0, nullable=False)  # PostHog unique users
    posthog_sessions = Column(Integer, default=0, nullable=False)  # PostHog sessions
    posthog_last_sync = Column(DateTime(timezone=True), nullable=True)  # Last PostHog sync

    # Legacy GA4 Integration (keeping for migration period)
    ga4_enabled = Column(Boolean, default=False, nullable=False)  # Enable GA4 tracking (deprecated)
    ga4_clicks = Column(Integer, default=0, nullable=False)  # GA4 event count (deprecated)
    ga4_users = Column(Integer, default=0, nullable=False)  # GA4 unique users (deprecated)
    ga4_sessions = Column(Integer, default=0, nullable=False)  # GA4 sessions (deprecated)
    ga4_last_sync = Column(DateTime(timezone=True), nullable=True)  # Last GA4 sync (deprecated)
    
    # Relationships
    # Note: No direct relationship to Video model to allow tracking new videos
    clicks = relationship("LinkClick", back_populates="utm_link", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_utm_video_active', 'video_id', 'is_active'),
        Index('idx_utm_created', 'created_at'),
    )

    @property
    def click_count(self):
        """Get the total number of clicks for this UTM link."""
        return len(self.clicks)

    @property
    def is_server_redirect(self):
        """Check if this link uses server redirect tracking."""
        return self.tracking_type == "server_redirect"

    @property
    def is_direct_ga4(self):
        """Check if this link uses direct GA4 tracking (deprecated)."""
        return self.tracking_type == "direct_ga4"

    @property
    def is_direct_posthog(self):
        """Check if this link uses direct PostHog tracking."""
        return self.tracking_type == "direct_posthog"

    @property
    def shareable_url(self):
        """Get the URL that should be shared publicly."""
        if self.is_direct_posthog or self.is_direct_ga4:
            # For Direct PostHog/GA4, always return the direct destination URL with UTM parameters
            # This ensures tracking works independently of localhost/server
            return self.direct_url or self.tracking_url
        else:
            # Server redirect links always use short URLs
            if self.pretty_slug:
                return f"/api/v1/go/{self.pretty_slug}"
            else:
                return f"/api/v1/r/{self.id}"

    @property
    def short_url(self):
        """Get the short URL for server-based tracking (optional for GA4)."""
        if self.pretty_slug:
            return f"/api/v1/go/{self.pretty_slug}"
        else:
            return f"/api/v1/r/{self.id}"

    @property
    def display_info(self):
        """Get display information for frontend."""
        if self.is_direct_posthog:
            return {
                "primary_url": self.direct_url or self.tracking_url,
                "primary_label": "Direct PostHog URL",
                "primary_description": "Goes directly to destination with UTM parameters - tracked by PostHog",
                "secondary_url": f"/api/v1/go/{self.pretty_slug}" if self.pretty_slug else f"/api/v1/r/{self.id}",
                "secondary_label": "Optional Short URL",
                "secondary_description": "Alternative short URL that redirects through your server"
            }
        elif self.is_direct_ga4:
            return {
                "primary_url": self.direct_url or self.tracking_url,
                "primary_label": "Direct GA4 URL (Legacy)",
                "primary_description": "Goes directly to destination with UTM parameters - tracked by GA4",
                "secondary_url": f"/api/v1/go/{self.pretty_slug}" if self.pretty_slug else f"/api/v1/r/{self.id}",
                "secondary_label": "Optional Short URL",
                "secondary_description": "Alternative short URL that redirects through your server"
            }
        else:
            return {
                "primary_url": f"/api/v1/go/{self.pretty_slug}" if self.pretty_slug else f"/api/v1/r/{self.id}",
                "primary_label": "Short Redirect URL",
                "primary_description": "Short branded URL that routes through your server",
                "secondary_url": None,
                "secondary_label": None,
                "secondary_description": None
            }

    def __repr__(self):
        return f"<UTMLink(id={self.id}, video_id={self.video_id}, tracking_type={self.tracking_type}, destination={self.destination_url[:50]}...)>"


class LinkClick(Base):
    """Individual click events for UTM tracking links."""
    __tablename__ = "link_clicks"

    id = Column(Integer, primary_key=True, index=True)
    utm_link_id = Column(Integer, ForeignKey("utm_links.id"), nullable=False, index=True)
    
    # Click metadata
    clicked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    referrer = Column(Text, nullable=True)
    
    # Optional tracking data
    country = Column(String(2), nullable=True)  # ISO country code
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    browser = Column(String(100), nullable=True)
    
    # Relationships
    utm_link = relationship("UTMLink", back_populates="clicks")
    
    # Indexes for analytics queries
    __table_args__ = (
        Index('idx_click_link_date', 'utm_link_id', 'clicked_at'),
        Index('idx_click_date', 'clicked_at'),
        Index('idx_click_country', 'country'),
    )

    def __repr__(self):
        return f"<LinkClick(id={self.id}, utm_link_id={self.utm_link_id}, clicked_at={self.clicked_at})>"
