"""
Historical metrics collection and management service.
Handles daily collection of channel and video metrics for trend analysis.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from loguru import logger

from app.models.channel import Channel, ChannelMetrics
from app.models.video import Video, VideoMetrics
from app.services.youtube import YouTubeDataService
from app.core.config import get_youtube_config


class HistoricalMetricsService:
    """Service for collecting and managing historical YouTube metrics."""
    
    def __init__(self, db: Session):
        self.db = db
        self.youtube_config = get_youtube_config()
    
    async def collect_daily_metrics(self, channel_id: str) -> Dict[str, Any]:
        """Collect and store daily metrics for channel and all videos."""
        try:
            logger.info(f"Starting daily metrics collection for channel {channel_id}")
            
            # Initialize YouTube service
            youtube_service = YouTubeDataService(self.db)
            
            # Collect channel metrics
            channel_metrics = await self._collect_channel_metrics(youtube_service, channel_id)
            
            # Collect video metrics for all videos
            video_metrics = await self._collect_video_metrics(youtube_service, channel_id)
            
            # Store metrics in database
            stored_channel_metrics = self._store_channel_metrics(channel_metrics)
            stored_video_metrics = self._store_video_metrics(video_metrics)
            
            result = {
                "status": "success",
                "timestamp": datetime.now(timezone.utc),
                "channel_metrics": stored_channel_metrics,
                "video_metrics_count": len(stored_video_metrics),
                "videos_processed": len(video_metrics)
            }
            
            logger.info(f"Daily metrics collection completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to collect daily metrics: {e}")
            raise
    
    async def _collect_channel_metrics(self, youtube_service: YouTubeDataService, channel_id: str) -> Dict[str, Any]:
        """Collect current channel metrics from YouTube API."""
        try:
            # Get fresh channel data
            channel_data = youtube_service.get_channel_info(channel_id)
            
            statistics = channel_data.get("statistics", {})
            snippet = channel_data.get("snippet", {})
            
            metrics = {
                "channel_id": channel_id,
                "date": datetime.now(timezone.utc),
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
                "view_count": int(statistics.get("viewCount", 0)),
                "video_count": int(statistics.get("videoCount", 0)),
                "data_source": "youtube_api"
            }
            
            # Calculate growth from previous day
            previous_metrics = self._get_previous_channel_metrics(channel_id)
            if previous_metrics:
                metrics["subscriber_growth"] = metrics["subscriber_count"] - previous_metrics.subscriber_count
                metrics["view_growth"] = metrics["view_count"] - previous_metrics.view_count
                
                # Calculate growth rates
                if previous_metrics.subscriber_count > 0:
                    metrics["subscriber_growth_rate"] = (metrics["subscriber_growth"] / previous_metrics.subscriber_count) * 100
                else:
                    metrics["subscriber_growth_rate"] = 0.0
                    
                if previous_metrics.view_count > 0:
                    metrics["view_growth_rate"] = (metrics["view_growth"] / previous_metrics.view_count) * 100
                else:
                    metrics["view_growth_rate"] = 0.0
            else:
                metrics["subscriber_growth"] = 0
                metrics["view_growth"] = 0
                metrics["subscriber_growth_rate"] = 0.0
                metrics["view_growth_rate"] = 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect channel metrics: {e}")
            raise
    
    async def _collect_video_metrics(self, youtube_service: YouTubeDataService, channel_id: str) -> List[Dict[str, Any]]:
        """Collect current metrics for all videos in the channel."""
        try:
            # Get all videos with high limit to capture everything
            videos_data = youtube_service.get_channel_videos(channel_id, max_results=200)
            
            video_metrics = []
            current_time = datetime.now(timezone.utc)
            
            for video_data in videos_data:
                try:
                    video_id = video_data["id"]
                    statistics = video_data.get("statistics", {})
                    
                    metrics = {
                        "video_id": video_id,
                        "date": current_time,
                        "view_count": int(statistics.get("viewCount", 0)),
                        "like_count": int(statistics.get("likeCount", 0)),
                        "comment_count": int(statistics.get("commentCount", 0)),
                        "data_source": "youtube_api"
                    }
                    
                    # Calculate growth from previous day
                    previous_metrics = self._get_previous_video_metrics(video_id)
                    if previous_metrics:
                        metrics["view_growth"] = metrics["view_count"] - previous_metrics.view_count
                        metrics["like_growth"] = metrics["like_count"] - previous_metrics.like_count
                        metrics["comment_growth"] = metrics["comment_count"] - previous_metrics.comment_count
                        
                        # Calculate growth rate
                        if previous_metrics.view_count > 0:
                            metrics["view_growth_rate"] = (metrics["view_growth"] / previous_metrics.view_count) * 100
                        else:
                            metrics["view_growth_rate"] = 0.0
                    else:
                        metrics["view_growth"] = 0
                        metrics["like_growth"] = 0
                        metrics["comment_growth"] = 0
                        metrics["view_growth_rate"] = 0.0
                    
                    # Calculate engagement rates
                    if metrics["view_count"] > 0:
                        metrics["like_rate"] = metrics["like_count"] / metrics["view_count"]
                        metrics["comment_rate"] = metrics["comment_count"] / metrics["view_count"]
                        metrics["engagement_rate"] = (metrics["like_count"] + metrics["comment_count"]) / metrics["view_count"]
                    else:
                        metrics["like_rate"] = 0.0
                        metrics["comment_rate"] = 0.0
                        metrics["engagement_rate"] = 0.0
                    
                    video_metrics.append(metrics)
                    
                except Exception as e:
                    logger.error(f"Failed to process video {video_data.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Collected metrics for {len(video_metrics)} videos")
            return video_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect video metrics: {e}")
            raise
    
    def _get_previous_channel_metrics(self, channel_id: str) -> Optional[ChannelMetrics]:
        """Get the most recent channel metrics for growth calculation."""
        return self.db.query(ChannelMetrics).filter(
            ChannelMetrics.channel_id == channel_id
        ).order_by(desc(ChannelMetrics.date)).first()
    
    def _get_previous_video_metrics(self, video_id: str) -> Optional[VideoMetrics]:
        """Get the most recent video metrics for growth calculation."""
        return self.db.query(VideoMetrics).filter(
            VideoMetrics.video_id == video_id
        ).order_by(desc(VideoMetrics.date)).first()
    
    def _store_channel_metrics(self, metrics_data: Dict[str, Any]) -> ChannelMetrics:
        """Store channel metrics in database."""
        try:
            # Check if metrics for today already exist
            today = metrics_data["date"].date()
            existing = self.db.query(ChannelMetrics).filter(
                and_(
                    ChannelMetrics.channel_id == metrics_data["channel_id"],
                    func.date(ChannelMetrics.date) == today
                )
            ).first()
            
            if existing:
                # Update existing record
                for key, value in metrics_data.items():
                    if key != "channel_id":  # Don't update the ID
                        setattr(existing, key, value)
                metrics = existing
            else:
                # Create new record
                metrics = ChannelMetrics(**metrics_data)
                self.db.add(metrics)
            
            self.db.commit()
            self.db.refresh(metrics)
            
            logger.info(f"Stored channel metrics for {metrics_data['channel_id']}")
            return metrics
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store channel metrics: {e}")
            raise
    
    def _store_video_metrics(self, video_metrics_list: List[Dict[str, Any]]) -> List[VideoMetrics]:
        """Store video metrics in database."""
        try:
            stored_metrics = []
            today = datetime.now(timezone.utc).date()
            
            for metrics_data in video_metrics_list:
                # Check if metrics for today already exist
                existing = self.db.query(VideoMetrics).filter(
                    and_(
                        VideoMetrics.video_id == metrics_data["video_id"],
                        func.date(VideoMetrics.date) == today
                    )
                ).first()
                
                if existing:
                    # Update existing record
                    for key, value in metrics_data.items():
                        if key != "video_id":  # Don't update the ID
                            setattr(existing, key, value)
                    metrics = existing
                else:
                    # Create new record
                    metrics = VideoMetrics(**metrics_data)
                    self.db.add(metrics)
                
                stored_metrics.append(metrics)
            
            self.db.commit()
            
            for metrics in stored_metrics:
                self.db.refresh(metrics)
            
            logger.info(f"Stored metrics for {len(stored_metrics)} videos")
            return stored_metrics
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store video metrics: {e}")
            raise
    
    def get_channel_growth_data(self, channel_id: str, days: int = 30) -> List[ChannelMetrics]:
        """Get historical channel growth data for charts."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        return self.db.query(ChannelMetrics).filter(
            and_(
                ChannelMetrics.channel_id == channel_id,
                ChannelMetrics.date >= start_date,
                ChannelMetrics.date <= end_date
            )
        ).order_by(ChannelMetrics.date).all()
    
    def get_video_performance_history(self, video_id: str, days: int = 30) -> List[VideoMetrics]:
        """Get historical video performance data."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        return self.db.query(VideoMetrics).filter(
            and_(
                VideoMetrics.video_id == video_id,
                VideoMetrics.date >= start_date,
                VideoMetrics.date <= end_date
            )
        ).order_by(VideoMetrics.date).all()
