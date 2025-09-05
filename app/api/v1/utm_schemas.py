"""
Pydantic schemas for UTM tracking API endpoints.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, HttpUrl, Field


class UTMLinkCreate(BaseModel):
    """Schema for creating a new UTM tracking link."""
    video_id: str = Field(..., description="YouTube video ID to associate with this link")
    destination_url: str = Field(..., description="The destination URL where users will be redirected")
    utm_content: Optional[str] = Field(None, description="Optional UTM content parameter")
    utm_term: Optional[str] = Field(None, description="Optional UTM term parameter")
    tracking_type: Literal["server_redirect", "direct_ga4", "direct_posthog"] = Field("direct_posthog", description="Tracking method: server_redirect for click tracking through our server, direct_ga4 for GA4-only tracking (legacy), direct_posthog for PostHog tracking (recommended)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "destination_url": "https://example.com/landing-page",
                "utm_content": "description_link",
                "utm_term": "youtube_traffic",
                "tracking_type": "direct_posthog"
            }
        }


class UTMLinkResponse(BaseModel):
    """Schema for UTM link response."""
    id: int
    video_id: str
    destination_url: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: Optional[str]
    utm_term: Optional[str]
    tracking_url: str
    pretty_slug: Optional[str] = Field(None, description="Pretty URL slug for user-friendly redirects")
    tracking_type: str = Field("server_redirect", description="Tracking method: server_redirect or direct_ga4")
    direct_url: Optional[str] = Field(None, description="Direct URL with UTM parameters for GA4-only tracking")
    shareable_url: Optional[str] = Field(None, description="The URL that should be shared publicly")
    created_at: datetime
    is_active: int
    click_count: int = Field(0, description="Total number of clicks on this UTM link")
    last_clicked: Optional[datetime] = Field(None, description="Timestamp of the most recent click")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "video_id": "dQw4w9WgXcQ",
                "destination_url": "https://example.com/landing-page",
                "utm_source": "youtube",
                "utm_medium": "video",
                "utm_campaign": "video_dQw4w9WgXcQ",
                "utm_content": "description_link",
                "utm_term": "youtube_traffic",
                "tracking_url": "https://example.com/landing-page?utm_source=youtube&utm_medium=video&utm_campaign=video_dQw4w9WgXcQ&utm_content=description_link&utm_term=youtube_traffic",
                "created_at": "2025-08-31T17:30:00Z",
                "is_active": 1,
                "click_count": 42,
                "last_clicked": "2025-08-31T18:15:00Z"
            }
        }


class LinkClickCreate(BaseModel):
    """Schema for recording a link click."""
    utm_link_id: int = Field(..., description="ID of the UTM link that was clicked")
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    referrer: Optional[str] = Field(None, description="Referrer URL")
    
    class Config:
        schema_extra = {
            "example": {
                "utm_link_id": 1,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ip_address": "192.168.1.1",
                "referrer": "https://youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }


class LinkClickResponse(BaseModel):
    """Schema for link click response."""
    id: int
    utm_link_id: int
    clicked_at: datetime
    user_agent: Optional[str]
    ip_address: Optional[str]
    referrer: Optional[str]
    
    class Config:
        from_attributes = True


class DailyClickData(BaseModel):
    """Schema for daily click data."""
    date: str
    clicks: int


class LinkAnalyticsResponse(BaseModel):
    """Schema for link analytics response."""
    utm_link_id: int
    video_id: str
    destination_url: str
    tracking_url: str
    total_clicks: int
    recent_clicks: int
    daily_clicks: List[DailyClickData]
    created_at: datetime
    is_active: int
    
    class Config:
        schema_extra = {
            "example": {
                "utm_link_id": 1,
                "video_id": "dQw4w9WgXcQ",
                "destination_url": "https://example.com/landing-page",
                "tracking_url": "https://example.com/landing-page?utm_source=youtube&utm_medium=video&utm_campaign=video_dQw4w9WgXcQ",
                "total_clicks": 150,
                "recent_clicks": 45,
                "daily_clicks": [
                    {"date": "2025-08-31", "clicks": 12},
                    {"date": "2025-08-30", "clicks": 8}
                ],
                "created_at": "2025-08-31T17:30:00Z",
                "is_active": 1
            }
        }


class VideoLinkData(BaseModel):
    """Schema for individual video link data."""
    id: int
    destination_url: str
    tracking_url: str
    clicks: int
    created_at: datetime


class VideoLinkPerformanceResponse(BaseModel):
    """Schema for video link performance response."""
    video_id: str
    video_title: str
    video_views: int
    total_links: int
    total_clicks: int
    click_through_rate: float
    views_to_clicks_ratio: str
    links: List[VideoLinkData]
    
    class Config:
        schema_extra = {
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "video_title": "Never Gonna Give You Up",
                "video_views": 1000000,
                "total_links": 3,
                "total_clicks": 1500,
                "click_through_rate": 0.15,
                "views_to_clicks_ratio": "1:667",
                "links": [
                    {
                        "id": 1,
                        "destination_url": "https://example.com/landing-page",
                        "tracking_url": "https://example.com/landing-page?utm_source=youtube&utm_medium=video&utm_campaign=video_dQw4w9WgXcQ",
                        "clicks": 800,
                        "created_at": "2025-08-31T17:30:00Z"
                    }
                ]
            }
        }


class VideoTrafficCorrelationResponse(BaseModel):
    """Schema for video traffic correlation response."""
    video_id: str
    video_title: str
    publication_date: str
    video_views: int
    link_count: int
    total_clicks: int
    click_through_rate: float
    views_to_clicks_ratio: str
    
    class Config:
        schema_extra = {
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "video_title": "Never Gonna Give You Up",
                "publication_date": "2025-08-26T13:06:48",
                "video_views": 1000000,
                "link_count": 3,
                "total_clicks": 1500,
                "click_through_rate": 0.15,
                "views_to_clicks_ratio": "1:667"
            }
        }


class UTMLinksListResponse(BaseModel):
    """Schema for UTM links list response."""
    status: str = "success"
    message: Optional[str] = None
    timestamp: datetime
    total_links: int
    links: List[UTMLinkResponse]
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": None,
                "timestamp": "2025-08-31T17:30:00Z",
                "total_links": 5,
                "links": []
            }
        }


class VideoTrafficCorrelationListResponse(BaseModel):
    """Schema for video traffic correlation list response."""
    status: str = "success"
    message: Optional[str] = None
    timestamp: datetime
    total_videos: int
    correlation_data: List[VideoTrafficCorrelationResponse]
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": None,
                "timestamp": "2025-08-31T17:30:00Z",
                "total_videos": 10,
                "correlation_data": []
            }
        }
