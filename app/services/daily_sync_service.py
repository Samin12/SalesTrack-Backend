"""
Daily YouTube data synchronization service.
Handles scheduled syncing of YouTube data to reduce API calls and improve performance.
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.daily_sync import DailyYouTubeSync, YouTubeDataSnapshot, SyncConfiguration, SyncMetrics
from app.models.video import Video
from app.models.channel import Channel
from app.services.youtube import YouTubeDataService
from app.services.historical_metrics_service import HistoricalMetricsService
from app.core.config import get_youtube_config
from app.core.database import get_db

logger = logging.getLogger(__name__)


class DailySyncService:
    """Service for managing daily YouTube data synchronization."""
    
    def __init__(self, db: Session):
        self.db = db
        self.youtube_service = YouTubeDataService(db)
        self.historical_metrics_service = HistoricalMetricsService(db)
        self.config = get_youtube_config()
        
    async def check_sync_needed(self, channel_id: str) -> bool:
        """Check if a sync is needed for the given channel."""
        try:
            # Get sync configuration
            sync_config = self.db.query(SyncConfiguration).filter(
                SyncConfiguration.channel_id == channel_id
            ).first()
            
            if not sync_config or not sync_config.sync_enabled:
                return False
            
            # Check last successful sync
            last_sync = self.db.query(DailyYouTubeSync).filter(
                and_(
                    DailyYouTubeSync.channel_id == channel_id,
                    DailyYouTubeSync.sync_status == "completed"
                )
            ).order_by(desc(DailyYouTubeSync.completed_at)).first()
            
            if not last_sync:
                return True  # No previous sync found
            
            # Check if enough time has passed
            # Ensure both datetimes are timezone-aware
            now_utc = datetime.now(timezone.utc)
            completed_at = last_sync.completed_at
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)

            time_since_sync = now_utc - completed_at
            sync_interval = timedelta(hours=sync_config.sync_frequency_hours)
            
            return time_since_sync >= sync_interval
            
        except Exception as e:
            logger.error(f"Error checking sync needed: {e}")
            return False
    
    async def start_sync(self, channel_id: str, force: bool = False, reason: str = "Scheduled sync") -> str:
        """Start a new sync operation."""
        try:
            # Check if sync is already running
            running_sync = self.db.query(DailyYouTubeSync).filter(
                and_(
                    DailyYouTubeSync.channel_id == channel_id,
                    DailyYouTubeSync.sync_status == "running"
                )
            ).first()
            
            if running_sync and not force:
                raise ValueError("Sync already running for this channel")
            
            # Create new sync record
            sync_id = str(uuid.uuid4())
            sync_record = DailyYouTubeSync(
                sync_id=sync_id,
                channel_id=channel_id,
                sync_status="running",
                started_at=datetime.now(timezone.utc)
            )
            
            self.db.add(sync_record)
            self.db.commit()
            
            # Start sync in background
            asyncio.create_task(self._perform_sync(sync_id, channel_id, reason))
            
            return sync_id
            
        except Exception as e:
            logger.error(f"Error starting sync: {e}")
            raise
    
    async def _perform_sync(self, sync_id: str, channel_id: str, reason: str):
        """Perform the actual sync operation."""
        start_time = time.time()
        api_calls_made = 0
        videos_synced = 0
        error_message = None
        
        try:
            logger.info(f"Starting comprehensive sync {sync_id} for channel {channel_id}: {reason}")

            # Collect historical metrics (this includes channel and video data collection)
            metrics_result = await self.historical_metrics_service.collect_daily_metrics(channel_id)
            api_calls_made += 10  # Estimate for metrics collection

            # Fetch ALL videos from YouTube API for complete sync
            videos_data = self.youtube_service.get_all_channel_videos(channel_id)
            api_calls_made += len(videos_data) // 50 + 2  # More accurate API call estimation
            
            # Get channel info for snapshot
            channel_data = self.youtube_service.get_channel_info(channel_id)
            statistics = channel_data.get("statistics", {})
            snippet = channel_data.get("snippet", {})

            # Create data snapshot
            snapshot_data = {
                "channel_id": channel_id,
                "channel_title": snippet.get("title", ""),
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
                "view_count": int(statistics.get("viewCount", 0)),
                "video_count": len(videos_data),
                "videos": videos_data,
                "sync_timestamp": datetime.now(timezone.utc)
            }
            
            # Store snapshot in database
            snapshot = YouTubeDataSnapshot(
                sync_id=sync_id,
                channel_id=channel_id,
                channel_title=snapshot_data["channel_title"],
                subscriber_count=snapshot_data["subscriber_count"],
                view_count=snapshot_data["view_count"],
                video_count=snapshot_data["video_count"],
                videos_data=videos_data,
                sync_timestamp=snapshot_data["sync_timestamp"]
            )
            
            self.db.add(snapshot)
            
            # Update/create video records in database
            videos_synced = await self._update_video_records(videos_data, channel_id)
            
            # Update channel record
            await self._update_channel_record(channel_data, channel_id)
            
            # Mark sync as completed
            sync_record = self.db.query(DailyYouTubeSync).filter(
                DailyYouTubeSync.sync_id == sync_id
            ).first()
            
            if sync_record:
                sync_record.sync_status = "completed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.videos_synced = videos_synced
                sync_record.api_calls_made = api_calls_made
                sync_record.sync_duration_seconds = time.time() - start_time
            
            self.db.commit()
            
            logger.info(f"Sync {sync_id} completed successfully. Videos synced: {videos_synced}, API calls: {api_calls_made}")
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Sync {sync_id} failed: {error_message}")
            
            # Mark sync as failed
            sync_record = self.db.query(DailyYouTubeSync).filter(
                DailyYouTubeSync.sync_id == sync_id
            ).first()
            
            if sync_record:
                sync_record.sync_status = "failed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.error_message = error_message
                sync_record.api_calls_made = api_calls_made
                sync_record.sync_duration_seconds = time.time() - start_time
            
            self.db.commit()
            
        finally:
            # Record metrics
            await self._record_sync_metrics(sync_id, channel_id, start_time, api_calls_made, videos_synced)
    
    async def _update_video_records(self, videos_data: List[Dict], channel_id: str) -> int:
        """Update video records in database with fresh YouTube data."""
        videos_updated = 0
        
        try:
            for video_data in videos_data:
                video_id = video_data.get("video_id")
                if not video_id:
                    continue
                
                # Check if video exists
                existing_video = self.db.query(Video).filter(
                    Video.video_id == video_id
                ).first()
                
                if existing_video:
                    # Update existing video
                    existing_video.title = video_data.get("title", existing_video.title)
                    existing_video.view_count = video_data.get("view_count", existing_video.view_count)
                    existing_video.like_count = video_data.get("like_count", existing_video.like_count)
                    existing_video.comment_count = video_data.get("comment_count", existing_video.comment_count)
                    existing_video.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new video record
                    new_video = Video(
                        video_id=video_id,
                        channel_id=channel_id,
                        title=video_data.get("title", ""),
                        description=video_data.get("description", ""),
                        published_at=video_data.get("published_at"),
                        view_count=video_data.get("view_count", 0),
                        like_count=video_data.get("like_count", 0),
                        comment_count=video_data.get("comment_count", 0),
                        duration=video_data.get("duration_seconds"),
                        thumbnail_url=video_data.get("thumbnail_url", ""),
                        is_active=True
                    )
                    self.db.add(new_video)
                
                videos_updated += 1
            
            return videos_updated
            
        except Exception as e:
            logger.error(f"Error updating video records: {e}")
            return videos_updated
    
    async def _update_channel_record(self, channel_data: Dict, channel_id: str):
        """Update channel record with fresh YouTube data."""
        try:
            existing_channel = self.db.query(Channel).filter(
                Channel.channel_id == channel_id
            ).first()
            
            if existing_channel:
                existing_channel.title = channel_data.get("title", existing_channel.title)
                existing_channel.subscriber_count = channel_data.get("subscriber_count", existing_channel.subscriber_count)
                existing_channel.view_count = channel_data.get("view_count", existing_channel.view_count)
                existing_channel.video_count = channel_data.get("video_count", existing_channel.video_count)
                existing_channel.updated_at = datetime.now(timezone.utc)
            else:
                # Create new channel record
                new_channel = Channel(
                    channel_id=channel_id,
                    title=channel_data.get("title", ""),
                    description=channel_data.get("description", ""),
                    subscriber_count=channel_data.get("subscriber_count", 0),
                    view_count=channel_data.get("view_count", 0),
                    video_count=channel_data.get("video_count", 0),
                    is_active=True
                )
                self.db.add(new_channel)
                
        except Exception as e:
            logger.error(f"Error updating channel record: {e}")
    
    async def _record_sync_metrics(self, sync_id: str, channel_id: str, start_time: float, api_calls: int, videos_processed: int):
        """Record sync performance metrics."""
        try:
            duration = time.time() - start_time
            
            metrics = SyncMetrics(
                sync_id=sync_id,
                channel_id=channel_id,
                total_duration_seconds=duration,
                api_calls_made=api_calls,
                videos_processed=videos_processed,
                data_transferred_bytes=0,  # Could be calculated if needed
                videos_updated=videos_processed,
                videos_added=0,  # Could be tracked separately
                videos_removed=0
            )
            
            self.db.add(metrics)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error recording sync metrics: {e}")
