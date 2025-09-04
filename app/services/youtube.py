"""
YouTube Data API v3 integration service.
"""
import isodate
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings, get_youtube_config
from app.models.channel import Channel, ChannelMetrics
from app.models.video import Video, VideoMetrics
from app.models.traffic import YouTubeAnalytics
from app.services.auth import AuthService
from app.services.youtube_scraper import YouTubeScraperService


class YouTubeDataService:
    """Service for interacting with YouTube Data API v3."""
    
    def __init__(self, db: Session, access_token: Optional[str] = None):
        self.db = db
        self.youtube_config = get_youtube_config()
        self.access_token = access_token
        self.youtube_service = None
        self.analytics_service = None
        self.scraper = YouTubeScraperService()
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize YouTube API services."""
        try:
            if self.access_token:
                # Use OAuth credentials
                credentials = Credentials(token=self.access_token)
                self.youtube_service = build('youtube', 'v3', credentials=credentials)
                self.analytics_service = build('youtubeAnalytics', 'v2', credentials=credentials)
            else:
                # Use API key for public data
                self.youtube_service = build('youtube', 'v3', developerKey=self.youtube_config["api_key"])
                
        except Exception as e:
            logger.error(f"Failed to initialize YouTube services: {e}")
            raise
    
    def get_channel_info(self, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """Get channel information."""
        try:
            target_channel_id = channel_id or self.youtube_config["channel_id"]
            
            request = self.youtube_service.channels().list(
                part="snippet,statistics,status,brandingSettings",
                id=target_channel_id
            )
            response = request.execute()
            
            if not response.get("items"):
                raise ValueError(f"Channel not found: {target_channel_id}")
            
            return response["items"][0]
            
        except HttpError as e:
            logger.error(f"YouTube API error getting channel info: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            raise
    
    def get_channel_videos(self, channel_id: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get videos from a channel with pagination support."""
        try:
            target_channel_id = channel_id or self.youtube_config["channel_id"]
            videos = []
            next_page_token = None

            # Set a reasonable upper limit to prevent infinite loops
            absolute_max = 1000  # YouTube channels rarely have more than this
            effective_max = min(max_results, absolute_max)

            while len(videos) < effective_max:
                # Calculate how many videos to request in this batch
                remaining = effective_max - len(videos)
                batch_size = min(50, remaining)  # YouTube API max is 50 per request

                # Get video IDs from channel
                request = self.youtube_service.search().list(
                    part="id",
                    channelId=target_channel_id,
                    type="video",
                    order="date",  # Newest first
                    maxResults=batch_size,
                    pageToken=next_page_token
                )
                response = request.execute()

                if not response.get("items"):
                    logger.info(f"No more videos found. Total collected: {len(videos)}")
                    break

                # Extract video IDs
                video_ids = [item["id"]["videoId"] for item in response["items"]]

                # Get detailed video information in batches (YouTube API limit is 50 IDs per request)
                for i in range(0, len(video_ids), 50):
                    batch_ids = video_ids[i:i+50]
                    video_request = self.youtube_service.videos().list(
                        part="snippet,statistics,status,contentDetails",
                        id=",".join(batch_ids)
                    )
                    video_response = video_request.execute()
                    videos.extend(video_response.get("items", []))

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    logger.info(f"Reached end of channel videos. Total collected: {len(videos)}")
                    break

            logger.info(f"Successfully fetched {len(videos)} videos from channel {target_channel_id}")
            return videos[:effective_max]

        except HttpError as e:
            logger.error(f"YouTube API error getting channel videos: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get channel videos: {e}")
            raise

    def get_all_channel_videos(self, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get ALL videos from a channel (no limit) for comprehensive sync."""
        try:
            target_channel_id = channel_id or self.youtube_config["channel_id"]

            # First, get the total video count from channel info
            channel_info = self.get_channel_info(target_channel_id)
            total_videos = int(channel_info.get("statistics", {}).get("videoCount", 0))

            logger.info(f"Channel has {total_videos} total videos. Fetching all...")

            # Fetch all videos with a high limit
            all_videos = self.get_channel_videos(target_channel_id, max_results=total_videos + 10)

            logger.info(f"Successfully fetched {len(all_videos)} out of {total_videos} total videos")
            return all_videos

        except Exception as e:
            logger.error(f"Failed to get all channel videos: {e}")
            raise
    
    def get_video_analytics(self, video_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get analytics data for a specific video."""
        if not self.analytics_service:
            logger.warning("Analytics service not available - OAuth required")
            return {}
        
        try:
            request = self.analytics_service.reports().query(
                ids=f"channel=={self.youtube_config['channel_id']}",
                startDate=start_date.strftime("%Y-%m-%d"),
                endDate=end_date.strftime("%Y-%m-%d"),
                metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares,subscribersGained",
                dimensions="video",
                filters=f"video=={video_id}",
                sort="-views"
            )
            response = request.execute()
            return response
            
        except HttpError as e:
            logger.error(f"YouTube Analytics API error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to get video analytics: {e}")
            return {}
    
    def get_channel_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get analytics data for the channel."""
        if not self.analytics_service:
            logger.warning("Analytics service not available - OAuth required")
            return {}
        
        try:
            request = self.analytics_service.reports().query(
                ids=f"channel=={self.youtube_config['channel_id']}",
                startDate=start_date.strftime("%Y-%m-%d"),
                endDate=end_date.strftime("%Y-%m-%d"),
                metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost",
                dimensions="day"
            )
            response = request.execute()
            return response
            
        except HttpError as e:
            logger.error(f"YouTube Analytics API error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to get channel analytics: {e}")
            return {}
    
    def save_channel_data(self, channel_data: Dict[str, Any]) -> Channel:
        """Save channel data to database."""
        try:
            channel_id = channel_data["id"]
            snippet = channel_data["snippet"]
            statistics = channel_data.get("statistics", {})
            
            # Check if channel exists
            existing_channel = self.db.query(Channel).filter(
                Channel.channel_id == channel_id
            ).first()
            
            if existing_channel:
                # Update existing channel
                existing_channel.channel_name = snippet.get("title", "")
                existing_channel.channel_description = snippet.get("description", "")
                existing_channel.subscriber_count = int(statistics.get("subscriberCount", 0))
                existing_channel.video_count = int(statistics.get("videoCount", 0))
                existing_channel.view_count = int(statistics.get("viewCount", 0))
                existing_channel.last_updated = datetime.utcnow()
                channel = existing_channel
            else:
                # Create new channel
                published_at = None
                if snippet.get("publishedAt"):
                    published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                
                channel = Channel(
                    channel_id=channel_id,
                    channel_handle=self.youtube_config.get("channel_handle", ""),
                    channel_name=snippet.get("title", ""),
                    channel_description=snippet.get("description", ""),
                    custom_url=snippet.get("customUrl", ""),
                    published_at=published_at,
                    country=snippet.get("country", ""),
                    default_language=snippet.get("defaultLanguage", ""),
                    subscriber_count=int(statistics.get("subscriberCount", 0)),
                    video_count=int(statistics.get("videoCount", 0)),
                    view_count=int(statistics.get("viewCount", 0)),
                    last_updated=datetime.utcnow()
                )
                self.db.add(channel)
            
            self.db.commit()
            self.db.refresh(channel)
            return channel
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save channel data: {e}")
            raise
    
    def save_video_data(self, video_data: Dict[str, Any], channel_id: str) -> Video:
        """Save video data to database."""
        try:
            video_id = video_data["id"]
            snippet = video_data["snippet"]
            statistics = video_data.get("statistics", {})
            content_details = video_data.get("contentDetails", {})
            
            # Check if video exists
            existing_video = self.db.query(Video).filter(
                Video.video_id == video_id
            ).first()
            
            # Parse duration
            duration_seconds = 0
            if content_details.get("duration"):
                try:
                    duration = isodate.parse_duration(content_details["duration"])
                    duration_seconds = int(duration.total_seconds())
                except Exception as e:
                    logger.warning(f"Failed to parse duration: {e}")
            
            if existing_video:
                # Update existing video
                existing_video.title = snippet.get("title", "")
                existing_video.description = snippet.get("description", "")
                existing_video.view_count = int(statistics.get("viewCount", 0))
                existing_video.like_count = int(statistics.get("likeCount", 0))
                existing_video.comment_count = int(statistics.get("commentCount", 0))
                existing_video.last_updated = datetime.utcnow()
                video = existing_video
            else:
                # Create new video
                published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                
                video = Video(
                    video_id=video_id,
                    channel_id=channel_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    published_at=published_at,
                    duration=content_details.get("duration", ""),
                    duration_seconds=duration_seconds,
                    category_id=snippet.get("categoryId", ""),
                    default_language=snippet.get("defaultLanguage", ""),
                    privacy_status=video_data.get("status", {}).get("privacyStatus", ""),
                    view_count=int(statistics.get("viewCount", 0)),
                    like_count=int(statistics.get("likeCount", 0)),
                    comment_count=int(statistics.get("commentCount", 0)),
                    tags=",".join(snippet.get("tags", [])),
                    thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    last_updated=datetime.utcnow()
                )
                self.db.add(video)
            
            self.db.commit()
            self.db.refresh(video)
            return video
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save video data: {e}")
            raise

    def get_enhanced_channel_info(self, channel_handle: str = None) -> Channel:
        """
        Get enhanced channel information using yt-dlp scraper.
        Falls back to API data if available.
        """
        try:
            # Use the configured channel handle if none provided
            if not channel_handle:
                channel_handle = self.youtube_config.get("channel_handle", "@SaminYasar_")

            # Get data from scraper
            scraper_data = self.scraper.get_channel_info(channel_handle)

            # Check if channel exists in database
            channel = self.db.query(Channel).filter(
                Channel.channel_id == scraper_data["channel_id"]
            ).first()

            if channel:
                # Update existing channel with fresh data
                channel.channel_name = scraper_data["channel_name"]
                channel.channel_handle = scraper_data["channel_handle"]
                channel.channel_description = scraper_data["description"]
                channel.subscriber_count = scraper_data["subscriber_count"]
                channel.last_updated = datetime.utcnow()
            else:
                # Create new channel
                channel = Channel(
                    channel_id=scraper_data["channel_id"],
                    channel_name=scraper_data["channel_name"],
                    channel_handle=scraper_data["channel_handle"],
                    channel_description=scraper_data["description"],
                    subscriber_count=scraper_data["subscriber_count"],
                    video_count=0,  # Will be updated when fetching videos
                    view_count=0,   # Will be updated when fetching videos
                    is_active=True,
                    last_updated=datetime.utcnow(),
                    published_at=datetime.utcnow()  # Placeholder
                )
                self.db.add(channel)

            self.db.commit()
            self.db.refresh(channel)
            return channel

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to get enhanced channel info: {e}")
            raise

    def sync_channel_videos(self, channel_handle: str = None, limit: int = 50) -> List[Video]:
        """
        Sync channel videos using yt-dlp scraper.
        Updates database with fresh video data.
        """
        try:
            # Use the configured channel handle if none provided
            if not channel_handle:
                channel_handle = self.youtube_config.get("channel_handle", "@SaminYasar_")

            # Get videos from scraper
            videos_data = self.scraper.get_channel_videos(channel_handle, limit)

            # Get or create channel
            channel = self.get_enhanced_channel_info(channel_handle)

            synced_videos = []
            total_views = 0

            for video_data in videos_data["videos"]:
                # Check if video exists
                video = self.db.query(Video).filter(
                    Video.video_id == video_data["video_id"]
                ).first()

                if video:
                    # Update existing video
                    video.title = video_data["title"]
                    video.description = video_data["description"]
                    video.view_count = video_data["view_count"]
                    video.like_count = video_data["like_count"]
                    video.comment_count = video_data["comment_count"]
                    video.duration = video_data["duration"]
                    video.thumbnail_url = video_data["thumbnail_url"]
                    video.tags = ",".join(video_data["tags"]) if video_data["tags"] else ""
                    video.last_updated = datetime.utcnow()
                else:
                    # Create new video
                    # Parse upload date
                    try:
                        upload_date = datetime.strptime(video_data["upload_date"], "%Y%m%d")
                    except:
                        upload_date = datetime.utcnow()

                    video = Video(
                        video_id=video_data["video_id"],
                        channel_id=channel.channel_id,
                        title=video_data["title"],
                        description=video_data["description"],
                        published_at=upload_date,
                        duration=video_data["duration"],
                        view_count=video_data["view_count"],
                        like_count=video_data["like_count"],
                        comment_count=video_data["comment_count"],
                        thumbnail_url=video_data["thumbnail_url"],
                        tags=",".join(video_data["tags"]) if video_data["tags"] else "",
                        privacy_status="public",
                        is_active=True,
                        last_updated=datetime.utcnow()
                    )
                    self.db.add(video)

                synced_videos.append(video)
                total_views += video_data["view_count"]

            # Update channel totals
            channel.video_count = len(synced_videos)
            channel.view_count = total_views
            channel.last_updated = datetime.utcnow()

            self.db.commit()

            # Refresh all objects
            for video in synced_videos:
                self.db.refresh(video)
            self.db.refresh(channel)

            logger.info(f"Synced {len(synced_videos)} videos for channel {channel_handle}")
            return synced_videos

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to sync channel videos: {e}")
            raise
