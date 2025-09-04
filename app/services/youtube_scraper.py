"""
Enhanced YouTube Data Service using yt-dlp
This service fetches comprehensive YouTube data without requiring OAuth
"""
import json
import subprocess
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class YouTubeScraperService:
    """Enhanced YouTube data scraper using yt-dlp"""
    
    def __init__(self):
        self.base_cmd = ['yt-dlp', '--no-download', '--print-json']
    
    def get_channel_info(self, channel_identifier: str) -> Dict[str, Any]:
        """
        Get channel information by handle or ID
        Args:
            channel_identifier: Channel handle (@username) or channel ID (UC...)
        """
        try:
            # Format channel URL
            if channel_identifier.startswith('@'):
                channel_url = f"https://www.youtube.com/{channel_identifier}"
            elif channel_identifier.startswith('UC'):
                channel_url = f"https://www.youtube.com/channel/{channel_identifier}"
            else:
                channel_url = f"https://www.youtube.com/@{channel_identifier}"
            
            # Get channel info using yt-dlp
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--playlist-end', '1',  # Just get one video to extract channel info
                channel_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                raise Exception(f"Failed to fetch channel info: {result.stderr}")
            
            # Parse the first video's metadata to get channel info
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                raise Exception("No data returned from yt-dlp")
            
            video_data = json.loads(lines[0])
            
            # Extract channel information from video metadata
            channel_info = {
                'channel_id': video_data.get('channel_id', ''),
                'channel_name': video_data.get('channel', ''),
                'channel_handle': channel_identifier if channel_identifier.startswith('@') else f"@{video_data.get('uploader', '')}",
                'channel_url': video_data.get('channel_url', ''),
                'subscriber_count': video_data.get('channel_follower_count', 0),
                'description': video_data.get('description', ''),
                'avatar_url': video_data.get('channel_thumbnails', [{}])[-1].get('url', '') if video_data.get('channel_thumbnails') else '',
                'is_verified': video_data.get('channel_is_verified', False),
                'upload_date': video_data.get('upload_date', ''),
                'view_count': 0,  # Will be calculated from videos
                'video_count': 0  # Will be calculated from videos
            }
            
            return channel_info
            
        except subprocess.TimeoutExpired:
            raise Exception("Request timed out")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise Exception("Failed to parse channel data")
        except Exception as e:
            logger.error(f"Error fetching channel info: {e}")
            raise
    
    def get_channel_videos(self, channel_identifier: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get recent videos from a channel
        Args:
            channel_identifier: Channel handle (@username) or channel ID (UC...)
            limit: Maximum number of videos to fetch
        """
        try:
            # Format channel URL
            if channel_identifier.startswith('@'):
                channel_url = f"https://www.youtube.com/{channel_identifier}/videos"
            elif channel_identifier.startswith('UC'):
                channel_url = f"https://www.youtube.com/channel/{channel_identifier}/videos"
            else:
                channel_url = f"https://www.youtube.com/@{channel_identifier}/videos"
            
            # Get videos using yt-dlp
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--playlist-end', str(limit),
                '--no-download',
                channel_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                raise Exception(f"Failed to fetch videos: {result.stderr}")
            
            videos = []
            total_views = 0
            
            # Parse each line as a separate JSON object
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    video_data = json.loads(line)
                    
                    # Extract video information
                    video_info = {
                        'video_id': video_data.get('id', ''),
                        'title': video_data.get('title', ''),
                        'description': video_data.get('description', ''),
                        'upload_date': video_data.get('upload_date', ''),
                        'duration': video_data.get('duration', 0),
                        'view_count': video_data.get('view_count', 0),
                        'like_count': video_data.get('like_count', 0),
                        'comment_count': video_data.get('comment_count', 0),
                        'thumbnail_url': video_data.get('thumbnail', ''),
                        'tags': video_data.get('tags', []),
                        'categories': video_data.get('categories', []),
                        'webpage_url': video_data.get('webpage_url', ''),
                        'is_live': video_data.get('is_live', False),
                        'was_live': video_data.get('was_live', False)
                    }
                    
                    videos.append(video_info)
                    total_views += video_info['view_count']
                    
                except json.JSONDecodeError:
                    continue
            
            return {
                'videos': videos,
                'total_videos': len(videos),
                'total_views': total_views,
                'channel_info': videos[0] if videos else None
            }
            
        except subprocess.TimeoutExpired:
            raise Exception("Request timed out")
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            raise
    
    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific video
        Args:
            video_id: YouTube video ID
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                raise Exception(f"Failed to fetch video details: {result.stderr}")
            
            video_data = json.loads(result.stdout.strip())
            
            # Extract detailed video information
            video_info = {
                'video_id': video_data.get('id', ''),
                'title': video_data.get('title', ''),
                'description': video_data.get('description', ''),
                'upload_date': video_data.get('upload_date', ''),
                'duration': video_data.get('duration', 0),
                'view_count': video_data.get('view_count', 0),
                'like_count': video_data.get('like_count', 0),
                'comment_count': video_data.get('comment_count', 0),
                'thumbnail_url': video_data.get('thumbnail', ''),
                'tags': video_data.get('tags', []),
                'categories': video_data.get('categories', []),
                'webpage_url': video_data.get('webpage_url', ''),
                'channel_id': video_data.get('channel_id', ''),
                'channel_name': video_data.get('channel', ''),
                'channel_url': video_data.get('channel_url', ''),
                'is_live': video_data.get('is_live', False),
                'was_live': video_data.get('was_live', False),
                'availability': video_data.get('availability', 'public')
            }
            
            return video_info
            
        except subprocess.TimeoutExpired:
            raise Exception("Request timed out")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise Exception("Failed to parse video data")
        except Exception as e:
            logger.error(f"Error fetching video details: {e}")
            raise
    
    def search_videos(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for videos on YouTube
        Args:
            query: Search query
            limit: Maximum number of results
        """
        try:
            search_url = f"ytsearch{limit}:{query}"
            
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                search_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                raise Exception(f"Failed to search videos: {result.stderr}")
            
            videos = []
            
            # Parse each line as a separate JSON object
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    video_data = json.loads(line)
                    
                    video_info = {
                        'video_id': video_data.get('id', ''),
                        'title': video_data.get('title', ''),
                        'channel_name': video_data.get('channel', ''),
                        'channel_id': video_data.get('channel_id', ''),
                        'upload_date': video_data.get('upload_date', ''),
                        'duration': video_data.get('duration', 0),
                        'view_count': video_data.get('view_count', 0),
                        'thumbnail_url': video_data.get('thumbnail', ''),
                        'webpage_url': video_data.get('webpage_url', '')
                    }
                    
                    videos.append(video_info)
                    
                except json.JSONDecodeError:
                    continue
            
            return videos
            
        except subprocess.TimeoutExpired:
            raise Exception("Request timed out")
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            raise
    
    def get_trending_videos(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get trending videos"""
        try:
            return self.search_videos("trending", limit)
        except Exception as e:
            logger.error(f"Error fetching trending videos: {e}")
            raise
