"""
YouTube Analytics API v2 integration service for historical data.
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings
from app.models.video import Video
from app.models.channel import Channel


class YouTubeAnalyticsService:
    """Service for YouTube Analytics API v2 - Historical data access."""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics_service = None
        self.credentials = None
        
        # OAuth 2.0 configuration
        self.client_config = self._load_oauth_config()
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/yt-analytics.readonly'
        ]
    
    def _load_oauth_config(self) -> Dict[str, Any]:
        """Load OAuth client configuration from environment or file."""
        try:
            # Try to load from environment variable (JSON string)
            if hasattr(settings, 'YOUTUBE_OAUTH_CONFIG') and settings.YOUTUBE_OAUTH_CONFIG:
                return json.loads(settings.YOUTUBE_OAUTH_CONFIG)
            
            # Try to load from file
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'youtube_oauth_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            
            raise FileNotFoundError("YouTube OAuth configuration not found")
            
        except Exception as e:
            logger.error(f"Failed to load YouTube OAuth config: {e}")
            raise
    
    def get_authorization_url(self, redirect_uri: str) -> str:
        """Get the authorization URL for OAuth flow."""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=redirect_uri
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent to get refresh token
            )
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=redirect_uri
            )
            
            flow.fetch_token(code=code)
            
            credentials = flow.credentials
            
            # Initialize the analytics service
            self.credentials = credentials
            self.analytics_service = build('youtubeAnalytics', 'v2', credentials=credentials)
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'expires_at': credentials.expiry.isoformat() if credentials.expiry else None,
                'token_type': 'Bearer'
            }
            
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh the access token using refresh token."""
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=self.client_config['web']['token_uri'],
                client_id=self.client_config['web']['client_id'],
                client_secret=self.client_config['web']['client_secret']
            )
            
            credentials.refresh(Request())
            
            self.credentials = credentials
            self.analytics_service = build('youtubeAnalytics', 'v2', credentials=credentials)
            
            return {
                'access_token': credentials.token,
                'expires_at': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise
    
    def initialize_with_token(self, access_token: str, refresh_token: Optional[str] = None):
        """Initialize service with existing tokens."""
        try:
            self.credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri=self.client_config['web']['token_uri'] if refresh_token else None,
                client_id=self.client_config['web']['client_id'] if refresh_token else None,
                client_secret=self.client_config['web']['client_secret'] if refresh_token else None
            )
            
            self.analytics_service = build('youtubeAnalytics', 'v2', credentials=self.credentials)
            
        except Exception as e:
            logger.error(f"Failed to initialize with token: {e}")
            raise
    
    def get_channel_analytics(self, channel_id: str, start_date: str, end_date: str, 
                            metrics: str = 'views,subscribersGained,subscribersLost') -> Dict[str, Any]:
        """Get channel analytics for a date range."""
        try:
            if not self.analytics_service:
                raise ValueError("Analytics service not initialized. Please authenticate first.")
            
            request = self.analytics_service.reports().query(
                ids=f'channel=={channel_id}',
                startDate=start_date,
                endDate=end_date,
                metrics=metrics,
                dimensions='day'
            )
            
            response = request.execute()
            return response
            
        except HttpError as e:
            logger.error(f"YouTube Analytics API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get channel analytics: {e}")
            raise
    
    def get_video_analytics(self, video_id: str, start_date: str, end_date: str,
                          metrics: str = 'views,likes,comments,estimatedMinutesWatched') -> Dict[str, Any]:
        """Get video analytics for a date range."""
        try:
            if not self.analytics_service:
                raise ValueError("Analytics service not initialized. Please authenticate first.")
            
            request = self.analytics_service.reports().query(
                ids=f'channel==MINE',  # Use MINE for authenticated user's channel
                startDate=start_date,
                endDate=end_date,
                metrics=metrics,
                dimensions='day',
                filters=f'video=={video_id}'
            )
            
            response = request.execute()
            return response
            
        except HttpError as e:
            logger.error(f"YouTube Analytics API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get video analytics: {e}")
            raise
    
    def get_weekly_performance(self, channel_id: str, weeks_back: int = 1) -> Dict[str, Any]:
        """Get weekly performance data."""
        try:
            # Calculate date range for the specified week
            today = datetime.now()
            days_since_sunday = (today.weekday() + 1) % 7
            current_week_start = today - timedelta(days=days_since_sunday)
            
            target_week_start = current_week_start - timedelta(weeks=weeks_back)
            target_week_end = target_week_start + timedelta(days=6)
            
            start_date = target_week_start.strftime('%Y-%m-%d')
            end_date = target_week_end.strftime('%Y-%m-%d')
            
            # Get analytics data
            analytics_data = self.get_channel_analytics(
                channel_id=channel_id,
                start_date=start_date,
                end_date=end_date,
                metrics='views,subscribersGained,subscribersLost,estimatedMinutesWatched'
            )
            
            # Process the data
            if 'rows' in analytics_data and analytics_data['rows']:
                total_views = sum(row[1] for row in analytics_data['rows'])  # views column
                subscribers_gained = sum(row[2] for row in analytics_data['rows'])  # subscribersGained
                subscribers_lost = sum(row[3] for row in analytics_data['rows'])  # subscribersLost
                watch_time_minutes = sum(row[4] for row in analytics_data['rows'])  # estimatedMinutesWatched
                
                return {
                    'week_start': start_date,
                    'week_end': end_date,
                    'total_views': total_views,
                    'subscribers_gained': subscribers_gained,
                    'subscribers_lost': subscribers_lost,
                    'net_subscribers': subscribers_gained - subscribers_lost,
                    'watch_time_minutes': watch_time_minutes,
                    'daily_data': analytics_data['rows']
                }
            else:
                return {
                    'week_start': start_date,
                    'week_end': end_date,
                    'total_views': 0,
                    'subscribers_gained': 0,
                    'subscribers_lost': 0,
                    'net_subscribers': 0,
                    'watch_time_minutes': 0,
                    'daily_data': []
                }
                
        except Exception as e:
            logger.error(f"Failed to get weekly performance: {e}")
            raise
