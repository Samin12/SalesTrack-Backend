# Models module initialization
# Import all models to ensure relationships are properly resolved
from app.models.base import BaseModel
from app.models.auth import OAuthToken, UserSession
from app.models.channel import Channel, ChannelMetrics
from app.models.video import Video, VideoMetrics
from app.models.traffic import WebsiteTraffic, ConversionEvent, YouTubeAnalytics
from app.models.weekly_metrics import WeeklyVideoMetrics, WeeklyChannelSummary, VideoPerformanceSnapshot
from app.models.daily_sync import DailyYouTubeSync, YouTubeDataSnapshot, SyncConfiguration, SyncMetrics
from app.models.utm_link import UTMLink, LinkClick

__all__ = [
    "BaseModel",
    "OAuthToken",
    "UserSession",
    "Channel",
    "ChannelMetrics",
    "Video",
    "VideoMetrics",
    "WebsiteTraffic",
    "ConversionEvent",
    "YouTubeAnalytics",
    "WeeklyVideoMetrics",
    "WeeklyChannelSummary",
    "VideoPerformanceSnapshot",
    "DailyYouTubeSync",
    "YouTubeDataSnapshot",
    "SyncConfiguration",
    "SyncMetrics",
    "UTMLink",
    "LinkClick"
]
