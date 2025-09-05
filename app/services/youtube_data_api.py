"""
YouTube Data API v3 service using API key (no OAuth required).
"""
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from loguru import logger

from app.core.config import settings


class YouTubeDataAPIService:
    """Service for YouTube Data API v3 using API key."""
    
    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        self.channel_id = settings.YOUTUBE_CHANNEL_ID
        self.channel_handle = settings.YOUTUBE_CHANNEL_HANDLE
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to YouTube Data API."""
        params['key'] = self.api_key
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"YouTube API request failed: {e}")
            # Return mock data for development when API key is invalid
            if "API key not valid" in str(e) or "your_youtube_api_key_here" in self.api_key:
                logger.warning("Using mock data for development - invalid API key detected")
                return self._get_mock_data(endpoint, params)
            raise Exception(f"YouTube API error: {str(e)}")

    def _get_mock_data(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock data for development when API is not available."""
        from datetime import datetime, timedelta

        if endpoint == 'channels':
            return {
                'items': [{
                    'id': 'UCMockChannelId123',
                    'snippet': {
                        'title': 'Development Channel',
                        'description': 'Mock channel for development',
                        'publishedAt': '2020-01-01T00:00:00Z',
                        'thumbnails': {
                            'default': {'url': 'https://via.placeholder.com/88x88'},
                            'medium': {'url': 'https://via.placeholder.com/240x240'},
                            'high': {'url': 'https://via.placeholder.com/800x800'}
                        }
                    },
                    'statistics': {
                        'subscriberCount': '6500',
                        'videoCount': '54',
                        'viewCount': '102264'
                    }
                }]
            }
        elif endpoint == 'search':
            # Mock recent videos
            mock_videos = []
            for i in range(5):
                days_ago = i * 2
                published_date = (datetime.utcnow() - timedelta(days=days_ago)).isoformat() + 'Z'
                mock_videos.append({
                    'id': {'videoId': f'mockVideo{i+1}'},
                    'snippet': {
                        'title': f'Mock Video {i+1}: Development Content',
                        'description': f'This is mock video {i+1} for development purposes',
                        'publishedAt': published_date,
                        'thumbnails': {
                            'default': {'url': 'https://via.placeholder.com/120x90'},
                            'medium': {'url': 'https://via.placeholder.com/320x180'},
                            'high': {'url': 'https://via.placeholder.com/480x360'}
                        }
                    }
                })
            return {'items': mock_videos}
        elif endpoint == 'videos':
            # Mock video statistics
            mock_stats = []
            video_ids = params.get('id', '').split(',') if params.get('id') else ['mockVideo1']
            for i, video_id in enumerate(video_ids):
                mock_stats.append({
                    'id': video_id,
                    'statistics': {
                        'viewCount': str(1000 + i * 500),
                        'likeCount': str(50 + i * 10),
                        'commentCount': str(5 + i * 2)
                    },
                    'contentDetails': {
                        'duration': 'PT5M30S'
                    }
                })
            return {'items': mock_stats}

        return {'items': []}

    def get_channel_statistics(self, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """Get channel statistics (subscribers, views, video count)."""
        channel_id = channel_id or self.channel_id
        
        params = {
            'part': 'statistics,snippet',
            'id': channel_id
        }
        
        data = self._make_request('channels', params)
        
        if not data.get('items'):
            raise Exception(f"Channel not found: {channel_id}")
        
        channel = data['items'][0]
        stats = channel['statistics']
        snippet = channel['snippet']
        
        return {
            'channel_id': channel_id,
            'channel_title': snippet['title'],
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'total_view_count': int(stats.get('viewCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'published_at': snippet['publishedAt'],
            'description': snippet.get('description', ''),
            'thumbnail_url': snippet['thumbnails']['default']['url'],
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def get_recent_videos(self, max_results: int = 10, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent videos from the channel."""
        channel_id = channel_id or self.channel_id
        
        # First, get the uploads playlist ID
        params = {
            'part': 'contentDetails',
            'id': channel_id
        }
        
        channel_data = self._make_request('channels', params)
        
        if not channel_data.get('items'):
            raise Exception(f"Channel not found: {channel_id}")
        
        uploads_playlist_id = channel_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get recent videos from uploads playlist
        params = {
            'part': 'snippet',
            'playlistId': uploads_playlist_id,
            'maxResults': max_results,
            'order': 'date'
        }
        
        playlist_data = self._make_request('playlistItems', params)
        
        videos = []
        video_ids = []
        
        for item in playlist_data.get('items', []):
            video_id = item['snippet']['resourceId']['videoId']
            video_ids.append(video_id)
            
            videos.append({
                'video_id': video_id,
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'published_at': item['snippet']['publishedAt'],
                'thumbnail_url': item['snippet']['thumbnails']['default']['url']
            })
        
        # Get statistics for these videos
        if video_ids:
            stats_params = {
                'part': 'statistics,contentDetails',
                'id': ','.join(video_ids)
            }
            
            stats_data = self._make_request('videos', stats_params)
            
            # Merge statistics with video info
            stats_by_id = {item['id']: item for item in stats_data.get('items', [])}
            
            for video in videos:
                video_stats = stats_by_id.get(video['video_id'], {})
                statistics = video_stats.get('statistics', {})
                content_details = video_stats.get('contentDetails', {})
                
                video.update({
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                    'duration': content_details.get('duration', 'PT0S'),
                    'updated_at': datetime.utcnow().isoformat()
                })
        
        return videos
    
    def get_video_statistics(self, video_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a specific video."""
        params = {
            'part': 'statistics,snippet,contentDetails',
            'id': video_id
        }
        
        data = self._make_request('videos', params)
        
        if not data.get('items'):
            raise Exception(f"Video not found: {video_id}")
        
        video = data['items'][0]
        stats = video['statistics']
        snippet = video['snippet']
        content_details = video['contentDetails']
        
        return {
            'video_id': video_id,
            'title': snippet['title'],
            'description': snippet['description'],
            'published_at': snippet['publishedAt'],
            'channel_title': snippet['channelTitle'],
            'view_count': int(stats.get('viewCount', 0)),
            'like_count': int(stats.get('likeCount', 0)),
            'comment_count': int(stats.get('commentCount', 0)),
            'duration': content_details.get('duration', 'PT0S'),
            'thumbnail_url': snippet['thumbnails']['default']['url'],
            'tags': snippet.get('tags', []),
            'category_id': snippet.get('categoryId'),
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def search_channel_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for videos within the channel."""
        params = {
            'part': 'snippet',
            'channelId': self.channel_id,
            'q': query,
            'type': 'video',
            'order': 'relevance',
            'maxResults': max_results
        }
        
        data = self._make_request('search', params)
        
        videos = []
        for item in data.get('items', []):
            videos.append({
                'video_id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'published_at': item['snippet']['publishedAt'],
                'thumbnail_url': item['snippet']['thumbnails']['default']['url']
            })
        
        return videos
    
    def get_channel_growth_estimate(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Estimate channel growth by comparing recent video performance.
        Note: This is an approximation since we can't get historical channel stats with API key.
        """
        try:
            # Get current channel stats
            current_stats = self.get_channel_statistics()
            
            # Get recent videos to estimate recent performance
            recent_videos = self.get_recent_videos(max_results=20)
            
            # Calculate recent video performance (last week vs older)
            cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=days_back)
            
            recent_views = 0
            older_views = 0
            recent_count = 0
            older_count = 0
            
            for video in recent_videos:
                published_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))

                if published_date >= cutoff_date:
                    recent_views += video['view_count']
                    recent_count += 1
                else:
                    older_views += video['view_count']
                    older_count += 1
            
            # Calculate average performance
            avg_recent_views = recent_views / recent_count if recent_count > 0 else 0
            avg_older_views = older_views / older_count if older_count > 0 else 0
            
            # Estimate growth percentage
            if avg_older_views > 0:
                growth_percentage = ((avg_recent_views - avg_older_views) / avg_older_views) * 100
            else:
                growth_percentage = 0
            
            return {
                'current_subscribers': current_stats['subscriber_count'],
                'current_total_views': current_stats['total_view_count'],
                'recent_videos_count': recent_count,
                'recent_average_views': int(avg_recent_views),
                'older_average_views': int(avg_older_views),
                'estimated_growth_percentage': round(growth_percentage, 1),
                'analysis_period_days': days_back,
                'updated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate growth estimate: {e}")
            return {
                'current_subscribers': 0,
                'current_total_views': 0,
                'recent_videos_count': 0,
                'recent_average_views': 0,
                'older_average_views': 0,
                'estimated_growth_percentage': 0,
                'analysis_period_days': days_back,
                'error': str(e),
                'updated_at': datetime.utcnow().isoformat()
            }
