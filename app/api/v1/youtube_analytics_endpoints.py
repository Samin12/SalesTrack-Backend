"""
YouTube Analytics API endpoints for historical data.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.services.youtube_analytics import YouTubeAnalyticsService
from app.models.oauth_token import YouTubeOAuthToken


router = APIRouter(prefix="/youtube-analytics", tags=["YouTube Analytics"])


def get_authenticated_youtube_service(db: Session = Depends(get_db)) -> YouTubeAnalyticsService:
    """Get an authenticated YouTube Analytics service."""
    # Get active OAuth token
    token = db.query(YouTubeOAuthToken).filter(
        YouTubeOAuthToken.is_active == True
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=401, 
            detail="No YouTube Analytics authentication found. Please complete OAuth flow first."
        )
    
    # Check if token needs refresh
    youtube_service = YouTubeAnalyticsService(db)
    
    if token.needs_refresh() and token.refresh_token:
        try:
            new_token_data = youtube_service.refresh_access_token(token.refresh_token)
            
            # Update token in database
            token.access_token = new_token_data['access_token']
            token.expires_at = datetime.fromisoformat(new_token_data['expires_at']) if new_token_data.get('expires_at') else None
            token.last_refreshed = datetime.utcnow()
            token.error_count = 0
            token.last_error = None
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            token.error_count += 1
            token.last_error = str(e)
            db.commit()
            
            if token.error_count >= 5:
                token.is_active = False
                db.commit()
                raise HTTPException(status_code=401, detail="Authentication expired. Please re-authenticate.")
    
    # Initialize service with current token
    youtube_service.initialize_with_token(token.access_token, token.refresh_token)
    return youtube_service


@router.get("/weekly-views")
async def get_weekly_youtube_views(
    weeks_back: int = Query(0, description="Number of weeks back (0 = current week)"),
    youtube_service: YouTubeAnalyticsService = Depends(get_authenticated_youtube_service),
    db: Session = Depends(get_db)
):
    """Get YouTube views for a specific week."""
    try:
        # Get the authenticated user's channel ID
        token = db.query(YouTubeOAuthToken).filter(YouTubeOAuthToken.is_active == True).first()
        
        if not token:
            raise HTTPException(status_code=401, detail="No authentication found")
        
        # Get weekly performance data
        weekly_data = youtube_service.get_weekly_performance(token.channel_id, weeks_back)
        
        return {
            "status": "success",
            "data": weekly_data,
            "weeks_back": weeks_back
        }
        
    except Exception as e:
        logger.error(f"Failed to get weekly YouTube views: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get YouTube data: {str(e)}")


@router.get("/channel-growth")
async def get_channel_growth(
    days: int = Query(30, description="Number of days to analyze"),
    youtube_service: YouTubeAnalyticsService = Depends(get_authenticated_youtube_service),
    db: Session = Depends(get_db)
):
    """Get channel growth analytics over time."""
    try:
        token = db.query(YouTubeOAuthToken).filter(YouTubeOAuthToken.is_active == True).first()
        
        if not token:
            raise HTTPException(status_code=401, detail="No authentication found")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get analytics data
        analytics_data = youtube_service.get_channel_analytics(
            channel_id=token.channel_id,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            metrics='views,subscribersGained,subscribersLost,estimatedMinutesWatched'
        )
        
        # Process the data
        if 'rows' in analytics_data and analytics_data['rows']:
            daily_data = []
            total_views = 0
            total_subscribers_gained = 0
            total_subscribers_lost = 0
            total_watch_time = 0
            
            for row in analytics_data['rows']:
                date_str = row[0]  # Date
                views = row[1] if len(row) > 1 else 0
                subs_gained = row[2] if len(row) > 2 else 0
                subs_lost = row[3] if len(row) > 3 else 0
                watch_time = row[4] if len(row) > 4 else 0
                
                daily_data.append({
                    'date': date_str,
                    'views': views,
                    'subscribers_gained': subs_gained,
                    'subscribers_lost': subs_lost,
                    'net_subscribers': subs_gained - subs_lost,
                    'watch_time_minutes': watch_time
                })
                
                total_views += views
                total_subscribers_gained += subs_gained
                total_subscribers_lost += subs_lost
                total_watch_time += watch_time
            
            return {
                "status": "success",
                "period": f"{days} days",
                "summary": {
                    "total_views": total_views,
                    "total_subscribers_gained": total_subscribers_gained,
                    "total_subscribers_lost": total_subscribers_lost,
                    "net_subscriber_change": total_subscribers_gained - total_subscribers_lost,
                    "total_watch_time_minutes": total_watch_time,
                    "average_daily_views": total_views // days if days > 0 else 0
                },
                "daily_data": daily_data
            }
        else:
            return {
                "status": "success",
                "period": f"{days} days",
                "summary": {
                    "total_views": 0,
                    "total_subscribers_gained": 0,
                    "total_subscribers_lost": 0,
                    "net_subscriber_change": 0,
                    "total_watch_time_minutes": 0,
                    "average_daily_views": 0
                },
                "daily_data": [],
                "message": "No data available for the specified period"
            }
        
    except Exception as e:
        logger.error(f"Failed to get channel growth: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get growth data: {str(e)}")


@router.get("/video-analytics/{video_id}")
async def get_video_analytics(
    video_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    youtube_service: YouTubeAnalyticsService = Depends(get_authenticated_youtube_service)
):
    """Get analytics for a specific video."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get video analytics
        analytics_data = youtube_service.get_video_analytics(
            video_id=video_id,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            metrics='views,likes,comments,estimatedMinutesWatched,averageViewDuration'
        )
        
        # Process the data
        if 'rows' in analytics_data and analytics_data['rows']:
            daily_data = []
            total_views = 0
            total_likes = 0
            total_comments = 0
            total_watch_time = 0
            
            for row in analytics_data['rows']:
                date_str = row[0]
                views = row[1] if len(row) > 1 else 0
                likes = row[2] if len(row) > 2 else 0
                comments = row[3] if len(row) > 3 else 0
                watch_time = row[4] if len(row) > 4 else 0
                
                daily_data.append({
                    'date': date_str,
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'watch_time_minutes': watch_time
                })
                
                total_views += views
                total_likes += likes
                total_comments += comments
                total_watch_time += watch_time
            
            return {
                "status": "success",
                "video_id": video_id,
                "period": f"{days} days",
                "summary": {
                    "total_views": total_views,
                    "total_likes": total_likes,
                    "total_comments": total_comments,
                    "total_watch_time_minutes": total_watch_time,
                    "average_daily_views": total_views // days if days > 0 else 0
                },
                "daily_data": daily_data
            }
        else:
            return {
                "status": "success",
                "video_id": video_id,
                "period": f"{days} days",
                "summary": {
                    "total_views": 0,
                    "total_likes": 0,
                    "total_comments": 0,
                    "total_watch_time_minutes": 0,
                    "average_daily_views": 0
                },
                "daily_data": [],
                "message": "No data available for this video in the specified period"
            }
        
    except Exception as e:
        logger.error(f"Failed to get video analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get video data: {str(e)}")


@router.get("/current-week-performance")
async def get_current_week_performance(
    youtube_service: YouTubeAnalyticsService = Depends(get_authenticated_youtube_service),
    db: Session = Depends(get_db)
):
    """Get current week's YouTube performance for the dashboard."""
    try:
        token = db.query(YouTubeOAuthToken).filter(YouTubeOAuthToken.is_active == True).first()
        
        if not token:
            raise HTTPException(status_code=401, detail="No authentication found")
        
        # Get current week (weeks_back=0) and last week (weeks_back=1) for comparison
        current_week = youtube_service.get_weekly_performance(token.channel_id, 0)
        last_week = youtube_service.get_weekly_performance(token.channel_id, 1)
        
        # Calculate growth percentage
        current_views = current_week.get('total_views', 0)
        last_views = last_week.get('total_views', 0)
        
        if last_views > 0:
            growth_percentage = ((current_views - last_views) / last_views) * 100
        else:
            growth_percentage = 0 if current_views == 0 else 100
        
        return {
            "status": "success",
            "current_week": current_week,
            "last_week": last_week,
            "growth_percentage": round(growth_percentage, 1),
            "comparison": {
                "views_change": current_views - last_views,
                "subscribers_change": current_week.get('net_subscribers', 0) - last_week.get('net_subscribers', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get current week performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance data: {str(e)}")
