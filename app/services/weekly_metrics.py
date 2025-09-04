"""
Weekly metrics service for tracking video and channel performance over time.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.video import Video
from app.models.channel import Channel
from app.models.weekly_metrics import WeeklyVideoMetrics, WeeklyChannelSummary, VideoPerformanceSnapshot

logger = logging.getLogger(__name__)


class WeeklyMetricsService:
    """Service for managing weekly video and channel metrics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_week_id(self, date_obj: date) -> str:
        """Get week ID in format YYYY-WXX (e.g., 2025-W35)."""
        year, week, _ = date_obj.isocalendar()
        return f"{year}-W{week:02d}"
    
    def get_week_dates(self, week_id: str) -> tuple[date, date]:
        """Get start and end dates for a week ID."""
        year, week = week_id.split('-W')
        year = int(year)
        week = int(week)
        
        # Get the first day of the year
        jan_1 = date(year, 1, 1)
        # Find the first Monday of the year
        first_monday = jan_1 + timedelta(days=(7 - jan_1.weekday()) % 7)
        if jan_1.weekday() > 0:  # If Jan 1 is not Monday
            first_monday = jan_1 + timedelta(days=7 - jan_1.weekday())
        
        # Calculate the start of the target week
        week_start = first_monday + timedelta(weeks=week - 1)
        week_end = week_start + timedelta(days=6)
        
        return week_start, week_end
    
    def create_weekly_video_metrics(
        self, 
        video_id: str, 
        channel_id: str, 
        week_date: date = None
    ) -> WeeklyVideoMetrics:
        """Create or update weekly metrics for a video."""
        if week_date is None:
            week_date = date.today()
        
        week_id = self.get_week_id(week_date)
        week_start, week_end = self.get_week_dates(week_id)
        
        # Check if metrics already exist for this week
        existing_metrics = self.db.query(WeeklyVideoMetrics).filter(
            WeeklyVideoMetrics.video_id == video_id,
            WeeklyVideoMetrics.week_id == week_id
        ).first()
        
        if existing_metrics:
            return existing_metrics
        
        # Get current video data
        video = self.db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")
        
        # Get previous week's metrics to calculate growth
        previous_week_date = week_date - timedelta(days=7)
        previous_week_id = self.get_week_id(previous_week_date)
        previous_metrics = self.db.query(WeeklyVideoMetrics).filter(
            WeeklyVideoMetrics.video_id == video_id,
            WeeklyVideoMetrics.week_id == previous_week_id
        ).first()
        
        # Calculate metrics
        view_count_start = previous_metrics.view_count_end if previous_metrics else 0
        views_gained = max(0, video.view_count - view_count_start)
        
        like_count_start = previous_metrics.like_count_end if previous_metrics else 0
        likes_gained = max(0, video.like_count - like_count_start)
        
        comment_count_start = previous_metrics.comment_count_end if previous_metrics else 0
        comments_gained = max(0, video.comment_count - comment_count_start)
        
        # Calculate growth rate
        view_growth_rate = 0.0
        if view_count_start > 0:
            view_growth_rate = (views_gained / view_count_start) * 100
        
        # Create new weekly metrics
        weekly_metrics = WeeklyVideoMetrics(
            video_id=video_id,
            channel_id=channel_id,
            week_id=week_id,
            week_start_date=week_start,
            week_end_date=week_end,
            view_count_start=view_count_start,
            view_count_end=video.view_count,
            views_gained=views_gained,
            like_count_start=like_count_start,
            like_count_end=video.like_count,
            likes_gained=likes_gained,
            comment_count_start=comment_count_start,
            comment_count_end=video.comment_count,
            comments_gained=comments_gained,
            view_growth_rate=view_growth_rate,
            engagement_growth_rate=0.0,  # Will be calculated later
            website_clicks=0,  # Will be updated from traffic data
            website_page_views=0,
            click_through_rate=0.0,
            data_source="youtube_scraper"
        )
        
        self.db.add(weekly_metrics)
        self.db.commit()
        self.db.refresh(weekly_metrics)
        
        return weekly_metrics
    
    def get_video_weekly_performance(
        self, 
        video_id: str, 
        weeks: int = 8
    ) -> List[WeeklyVideoMetrics]:
        """Get weekly performance data for a video."""
        return self.db.query(WeeklyVideoMetrics).filter(
            WeeklyVideoMetrics.video_id == video_id
        ).order_by(desc(WeeklyVideoMetrics.week_start_date)).limit(weeks).all()
    
    def get_channel_weekly_summary(
        self, 
        channel_id: str, 
        week_date: date = None
    ) -> WeeklyChannelSummary:
        """Get or create weekly summary for a channel."""
        if week_date is None:
            week_date = date.today()
        
        week_id = self.get_week_id(week_date)
        week_start, week_end = self.get_week_dates(week_id)
        
        # Check if summary already exists
        existing_summary = self.db.query(WeeklyChannelSummary).filter(
            WeeklyChannelSummary.channel_id == channel_id,
            WeeklyChannelSummary.week_id == week_id
        ).first()
        
        if existing_summary:
            return existing_summary
        
        # Get all video metrics for this week
        video_metrics = self.db.query(WeeklyVideoMetrics).filter(
            WeeklyVideoMetrics.channel_id == channel_id,
            WeeklyVideoMetrics.week_id == week_id
        ).all()
        
        # Calculate aggregate metrics
        total_views_gained = sum(m.views_gained for m in video_metrics)
        total_likes_gained = sum(m.likes_gained for m in video_metrics)
        total_comments_gained = sum(m.comments_gained for m in video_metrics)
        total_website_clicks = sum(m.website_clicks for m in video_metrics)
        total_website_page_views = sum(m.website_page_views for m in video_metrics)
        
        # Find top performing video
        top_video_metric = max(video_metrics, key=lambda m: m.views_gained) if video_metrics else None
        
        # Get channel data
        channel = self.db.query(Channel).filter(Channel.channel_id == channel_id).first()
        
        # Create summary
        summary = WeeklyChannelSummary(
            channel_id=channel_id,
            week_id=week_id,
            week_start_date=week_start,
            week_end_date=week_end,
            total_views_gained=total_views_gained,
            total_likes_gained=total_likes_gained,
            total_comments_gained=total_comments_gained,
            total_website_clicks=total_website_clicks,
            total_website_page_views=total_website_page_views,
            subscriber_count_end=channel.subscriber_count if channel else 0,
            subscribers_gained=0,  # Will be calculated with historical data
            videos_published=0,  # Will be calculated
            active_videos_count=len([m for m in video_metrics if m.views_gained > 0]),
            average_views_per_video=total_views_gained / len(video_metrics) if video_metrics else 0,
            top_video_id=top_video_metric.video_id if top_video_metric else None,
            top_video_views_gained=top_video_metric.views_gained if top_video_metric else 0,
            total_engagement_rate=0.0,  # Will be calculated
            average_ctr=0.0,  # Will be calculated
            data_completeness=1.0
        )
        
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        
        return summary
    
    def sync_weekly_metrics_for_channel(
        self, 
        channel_id: str, 
        weeks_back: int = 4
    ) -> Dict[str, Any]:
        """Sync weekly metrics for all videos in a channel."""
        try:
            # Get all videos for the channel
            videos = self.db.query(Video).filter(
                Video.channel_id == channel_id,
                Video.is_active == True
            ).all()
            
            synced_metrics = []
            current_date = date.today()
            
            # Create metrics for the last N weeks
            for week_offset in range(weeks_back):
                week_date = current_date - timedelta(weeks=week_offset)
                
                for video in videos:
                    try:
                        metrics = self.create_weekly_video_metrics(
                            video.video_id,
                            channel_id,
                            week_date
                        )
                        synced_metrics.append(metrics)
                    except Exception as e:
                        logger.error(f"Failed to create weekly metrics for video {video.video_id}: {e}")
                        continue
                
                # Create channel summary for this week
                try:
                    summary = self.get_channel_weekly_summary(channel_id, week_date)
                    logger.info(f"Created weekly summary for {channel_id}, week {summary.week_id}")
                except Exception as e:
                    logger.error(f"Failed to create weekly summary for {channel_id}: {e}")
            
            return {
                "success": True,
                "metrics_created": len(synced_metrics),
                "videos_processed": len(videos),
                "weeks_processed": weeks_back
            }
            
        except Exception as e:
            logger.error(f"Failed to sync weekly metrics: {e}")
            raise
    
    def get_trending_videos(
        self, 
        channel_id: str, 
        week_date: date = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending videos for a specific week."""
        if week_date is None:
            week_date = date.today()
        
        week_id = self.get_week_id(week_date)
        
        # Get videos with highest growth rate this week
        trending = self.db.query(WeeklyVideoMetrics).join(Video).filter(
            WeeklyVideoMetrics.channel_id == channel_id,
            WeeklyVideoMetrics.week_id == week_id
        ).order_by(desc(WeeklyVideoMetrics.view_growth_rate)).limit(limit).all()
        
        result = []
        for metric in trending:
            result.append({
                "video_id": metric.video_id,
                "title": metric.video.title,
                "views_gained": metric.views_gained,
                "growth_rate": metric.view_growth_rate,
                "total_views": metric.view_count_end,
                "website_clicks": metric.website_clicks
            })
        
        return result
