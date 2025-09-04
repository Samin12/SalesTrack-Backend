"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


# Base schemas
class BaseResponse(BaseModel):
    """Base response model."""
    status: str = "success"
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Channel schemas
class ChannelOverview(BaseModel):
    """Channel overview response schema."""
    channel_id: str
    channel_name: str
    channel_handle: str
    subscriber_count: int
    video_count: int
    view_count: int
    last_updated: datetime
    
    class Config:
        from_attributes = True


class ChannelGrowthMetrics(BaseModel):
    """Channel growth metrics schema."""
    date: datetime
    subscriber_count: int
    subscriber_growth: int
    subscriber_growth_rate: float
    view_count: int
    view_growth: int
    view_growth_rate: float
    
    class Config:
        from_attributes = True


class ChannelGrowthResponse(BaseResponse):
    """Channel growth response schema."""
    channel_id: str
    period_start: datetime
    period_end: datetime
    current_metrics: ChannelGrowthMetrics
    historical_data: List[ChannelGrowthMetrics]
    summary: Dict[str, Any]


# Video schemas
class VideoOverview(BaseModel):
    """Video overview schema."""
    video_id: str
    title: str
    published_at: datetime
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: Optional[int] = 0
    
    class Config:
        from_attributes = True


class VideoMetricsData(BaseModel):
    """Video metrics data schema."""
    date: datetime
    view_count: int
    view_growth: int
    view_growth_rate: float
    like_count: int
    comment_count: int
    engagement_rate: float
    
    class Config:
        from_attributes = True


class VideoPerformanceResponse(BaseResponse):
    """Video performance response schema."""
    video_id: str
    video_info: VideoOverview
    current_metrics: VideoMetricsData
    historical_data: List[VideoMetricsData]
    growth_analysis: Dict[str, Any]


class VideosListResponse(BaseResponse):
    """Videos list response schema."""
    total_videos: int
    videos: List[VideoOverview]
    top_performing: List[VideoOverview]
    fastest_growing: List[VideoOverview]


# Weekly Performance schemas (authentic YouTube data only)
class WeeklyVideoPerformance(BaseModel):
    """Weekly video performance schema - authentic YouTube metrics only."""
    video_id: str
    title: str
    published_at: datetime
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: Optional[int] = None
    views_this_week: Optional[int] = None  # None when historical data not available
    views_last_week: Optional[int] = None  # None when historical data not available
    weekly_growth_rate: Optional[float] = None  # None when historical data not available

    class Config:
        from_attributes = True


class WeeklySummary(BaseModel):
    """Weekly summary schema - authentic YouTube metrics only."""
    total_views_this_week: Optional[int] = None  # None when historical data not available
    total_views_last_week: Optional[int] = None  # None when historical data not available
    views_growth_rate: Optional[float] = None  # None when historical data not available
    active_videos: int
    total_videos: int


class WeeklyPerformanceResponse(BaseResponse):
    """Weekly performance response schema - authentic YouTube data only."""
    weekly_summary: WeeklySummary
    video_performance: List[WeeklyVideoPerformance]
    note: str = "Data based on authentic YouTube metrics only - no fabricated click data"


# Traffic schemas (placeholder - no real data available)
class WebsiteTrafficData(BaseModel):
    """Website traffic data schema - placeholder for future implementation."""
    date: datetime
    source: str
    page_views: int
    bounce_rate: float

    class Config:
        from_attributes = True


class TrafficResponse(BaseResponse):
    """Traffic response schema - placeholder for future implementation."""
    period_start: datetime
    period_end: datetime
    total_page_views: int
    traffic_data: List[WebsiteTrafficData]
    top_sources: List[Dict[str, Any]]
    note: str = "Traffic data is placeholder - implement real analytics tracking for accurate metrics"


# Analytics schemas
class AnalyticsOverviewResponse(BaseResponse):
    """Analytics overview response schema."""
    channel_overview: ChannelOverview
    recent_growth: Optional[ChannelGrowthMetrics]
    top_videos: List[VideoOverview]
    traffic_summary: Dict[str, Any]
    key_insights: List[str]


# Authentication schemas
class AuthURLResponse(BaseResponse):
    """OAuth authorization URL response."""
    authorization_url: str
    state: Optional[str] = None


class TokenResponse(BaseResponse):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Query parameter schemas
class DateRangeParams(BaseModel):
    """Date range query parameters."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    days: Optional[int] = Field(default=30, ge=1, le=365)


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=100)


class VideoQueryParams(DateRangeParams, PaginationParams):
    """Video query parameters."""
    sort_by: Optional[str] = Field(default="published_at", pattern="^(published_at|view_count|growth_rate)$")
    order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")


# Error schemas
class ErrorResponse(BaseModel):
    """Error response schema."""
    status: str = "error"
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Daily YouTube Data Synchronization schemas
class SyncStatus(str, Enum):
    """Sync status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class YouTubeDataSnapshot(BaseModel):
    """YouTube data snapshot schema for daily sync."""
    channel_id: str
    channel_title: str
    subscriber_count: int
    view_count: int
    video_count: int
    videos: List[Dict[str, Any]]  # Full video data from YouTube API
    sync_timestamp: datetime

    class Config:
        from_attributes = True


class DailyYouTubeSync(BaseModel):
    """Daily YouTube sync record schema."""
    sync_id: str
    channel_id: str
    sync_status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    videos_synced: int = 0
    api_calls_made: int = 0
    data_snapshot: Optional[YouTubeDataSnapshot] = None

    class Config:
        from_attributes = True


class SyncStatusResponse(BaseResponse):
    """Sync status response schema."""
    current_sync: Optional[DailyYouTubeSync] = None
    last_successful_sync: Optional[DailyYouTubeSync] = None
    next_scheduled_sync: datetime
    sync_frequency_hours: int = 24
    data_freshness_hours: Optional[float] = None
    is_sync_needed: bool = False


class SyncTriggerRequest(BaseModel):
    """Manual sync trigger request schema."""
    force_sync: bool = False
    reason: Optional[str] = "Manual trigger"


class SyncTriggerResponse(BaseResponse):
    """Manual sync trigger response schema."""
    sync_id: str
    sync_status: SyncStatus
    message: str
