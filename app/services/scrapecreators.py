"""
ScrapeCreators API integration service.
"""
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings, get_scrapecreators_config
from app.models.channel import Channel, ChannelMetrics
from app.models.video import Video, VideoMetrics


class ScrapeCreatorsService:
    """Service for interacting with ScrapeCreators API."""
    
    def __init__(self, db: Session):
        self.db = db
        self.config = get_scrapecreators_config()
        self.base_url = self.config["base_url"]
        self.api_key = self.config["api_key"]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to ScrapeCreators API."""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params or {},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"ScrapeCreators API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"ScrapeCreators API request error: {e}")
            raise
        except Exception as e:
            logger.error(f"ScrapeCreators API unexpected error: {e}")
            raise
    
    async def get_youtube_channel_data(self, channel_handle: str) -> Dict[str, Any]:
        """Get YouTube channel data from ScrapeCreators."""
        try:
            params = {
                "channel": channel_handle,
                "include_videos": True,
                "include_analytics": True
            }
            
            data = await self._make_request("/youtube/channel", params)
            return data
            
        except Exception as e:
            logger.error(f"Failed to get channel data from ScrapeCreators: {e}")
            raise
    
    async def get_youtube_video_data(self, video_id: str) -> Dict[str, Any]:
        """Get YouTube video data from ScrapeCreators."""
        try:
            params = {
                "video_id": video_id,
                "include_analytics": True,
                "include_comments": False  # Can be enabled if needed
            }
            
            data = await self._make_request("/youtube/video", params)
            return data
            
        except Exception as e:
            logger.error(f"Failed to get video data from ScrapeCreators: {e}")
            raise
    
    async def get_channel_growth_data(self, channel_handle: str, days: int = 30) -> Dict[str, Any]:
        """Get channel growth data over specified period."""
        try:
            params = {
                "channel": channel_handle,
                "days": days,
                "metrics": "subscribers,views,videos"
            }
            
            data = await self._make_request("/youtube/channel/growth", params)
            return data
            
        except Exception as e:
            logger.error(f"Failed to get channel growth data: {e}")
            raise
    
    async def get_trending_videos(self, channel_handle: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending videos for a channel."""
        try:
            params = {
                "channel": channel_handle,
                "limit": limit,
                "sort_by": "growth_rate",
                "period": "7d"
            }
            
            data = await self._make_request("/youtube/channel/trending", params)
            return data.get("videos", [])
            
        except Exception as e:
            logger.error(f"Failed to get trending videos: {e}")
            raise
    
    async def get_competitor_analysis(self, channel_handle: str, competitors: List[str]) -> Dict[str, Any]:
        """Get competitor analysis data."""
        try:
            params = {
                "channel": channel_handle,
                "competitors": ",".join(competitors),
                "metrics": "subscribers,views,engagement_rate"
            }
            
            data = await self._make_request("/youtube/analysis/competitors", params)
            return data
            
        except Exception as e:
            logger.error(f"Failed to get competitor analysis: {e}")
            raise
    
    def save_scraped_channel_metrics(self, scraped_data: Dict[str, Any], channel_id: str) -> ChannelMetrics:
        """Save scraped channel metrics to database."""
        try:
            metrics_data = scraped_data.get("metrics", {})
            
            # Create channel metrics entry
            channel_metrics = ChannelMetrics(
                channel_id=channel_id,
                date=datetime.utcnow(),
                subscriber_count=metrics_data.get("subscribers", 0),
                video_count=metrics_data.get("video_count", 0),
                view_count=metrics_data.get("total_views", 0),
                subscriber_growth=metrics_data.get("subscriber_growth", 0),
                subscriber_growth_rate=metrics_data.get("subscriber_growth_rate", 0.0),
                view_growth=metrics_data.get("view_growth", 0),
                view_growth_rate=metrics_data.get("view_growth_rate", 0.0),
                estimated_minutes_watched=metrics_data.get("estimated_minutes_watched", 0),
                average_view_duration=metrics_data.get("average_view_duration", 0.0),
                data_source="scrapecreators"
            )
            
            self.db.add(channel_metrics)
            self.db.commit()
            self.db.refresh(channel_metrics)
            
            logger.info(f"Saved scraped channel metrics for channel {channel_id}")
            return channel_metrics
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save scraped channel metrics: {e}")
            raise
    
    def save_scraped_video_metrics(self, scraped_data: Dict[str, Any], video_id: str) -> VideoMetrics:
        """Save scraped video metrics to database."""
        try:
            metrics_data = scraped_data.get("metrics", {})
            
            # Create video metrics entry
            video_metrics = VideoMetrics(
                video_id=video_id,
                date=datetime.utcnow(),
                view_count=metrics_data.get("views", 0),
                like_count=metrics_data.get("likes", 0),
                comment_count=metrics_data.get("comments", 0),
                view_growth=metrics_data.get("view_growth", 0),
                view_growth_rate=metrics_data.get("view_growth_rate", 0.0),
                like_growth=metrics_data.get("like_growth", 0),
                comment_growth=metrics_data.get("comment_growth", 0),
                like_rate=metrics_data.get("like_rate", 0.0),
                comment_rate=metrics_data.get("comment_rate", 0.0),
                engagement_rate=metrics_data.get("engagement_rate", 0.0),
                estimated_minutes_watched=metrics_data.get("estimated_minutes_watched", 0),
                average_view_duration=metrics_data.get("average_view_duration", 0.0),
                average_view_percentage=metrics_data.get("average_view_percentage", 0.0),
                data_source="scrapecreators"
            )
            
            self.db.add(video_metrics)
            self.db.commit()
            self.db.refresh(video_metrics)
            
            logger.info(f"Saved scraped video metrics for video {video_id}")
            return video_metrics
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save scraped video metrics: {e}")
            raise
    
    async def sync_channel_data(self, channel_handle: str) -> Dict[str, Any]:
        """Sync channel data from ScrapeCreators and save to database."""
        try:
            # Get channel data from ScrapeCreators
            scraped_data = await self.get_youtube_channel_data(channel_handle)
            
            # Extract channel info
            channel_info = scraped_data.get("channel", {})
            channel_id = channel_info.get("id")
            
            if not channel_id:
                raise ValueError("Channel ID not found in scraped data")
            
            # Save channel metrics
            if scraped_data.get("metrics"):
                self.save_scraped_channel_metrics(scraped_data, channel_id)
            
            # Save video metrics if available
            videos = scraped_data.get("videos", [])
            for video_data in videos:
                video_id = video_data.get("id")
                if video_id and video_data.get("metrics"):
                    self.save_scraped_video_metrics(video_data, video_id)
            
            return {
                "status": "success",
                "channel_id": channel_id,
                "videos_processed": len(videos),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to sync channel data: {e}")
            raise
