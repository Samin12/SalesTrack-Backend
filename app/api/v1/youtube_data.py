"""
YouTube Data API v3 endpoints using API key (no OAuth required).
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.services.youtube_data_api import YouTubeDataAPIService


router = APIRouter(prefix="/youtube-data", tags=["YouTube Data API"])


@router.get("/channel-stats")
async def get_channel_statistics():
    """Get current channel statistics (subscribers, views, video count)."""
    try:
        youtube_service = YouTubeDataAPIService()
        stats = youtube_service.get_channel_statistics()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get channel statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get channel data: {str(e)}")


@router.get("/recent-videos")
async def get_recent_videos(
    max_results: int = Query(10, description="Number of recent videos to fetch", ge=1, le=50)
):
    """Get recent videos with statistics."""
    try:
        youtube_service = YouTubeDataAPIService()
        videos = youtube_service.get_recent_videos(max_results=max_results)
        
        return {
            "status": "success",
            "data": videos,
            "count": len(videos)
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent videos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get videos: {str(e)}")


@router.get("/video/{video_id}")
async def get_video_statistics(video_id: str):
    """Get detailed statistics for a specific video."""
    try:
        youtube_service = YouTubeDataAPIService()
        video_stats = youtube_service.get_video_statistics(video_id)
        
        return {
            "status": "success",
            "data": video_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get video statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get video data: {str(e)}")


@router.get("/growth-estimate")
async def get_channel_growth_estimate(
    days_back: int = Query(7, description="Number of days to analyze for growth estimation", ge=1, le=30)
):
    """Get estimated channel growth based on recent video performance."""
    try:
        youtube_service = YouTubeDataAPIService()
        growth_data = youtube_service.get_channel_growth_estimate(days_back=days_back)
        
        return {
            "status": "success",
            "data": growth_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get growth estimate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate growth: {str(e)}")


@router.get("/dashboard-summary")
async def get_dashboard_summary():
    """Get comprehensive YouTube data for dashboard display."""
    try:
        youtube_service = YouTubeDataAPIService()
        
        # Get all the data needed for dashboard
        channel_stats = youtube_service.get_channel_statistics()
        recent_videos = youtube_service.get_recent_videos(max_results=5)
        growth_estimate = youtube_service.get_channel_growth_estimate(days_back=7)
        
        # Calculate this week's estimated views from recent videos
        from datetime import datetime, timedelta, timezone
        week_ago = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=7)

        this_week_views = 0
        this_week_videos = []

        for video in recent_videos:
            published_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
            if published_date >= week_ago:
                this_week_views += video['view_count']
                this_week_videos.append(video)
        
        # Format the response for the dashboard
        dashboard_data = {
            # Channel overview
            'channel_title': channel_stats['channel_title'],
            'total_subscribers': channel_stats['subscriber_count'],
            'total_views': channel_stats['total_view_count'],
            'total_videos': channel_stats['video_count'],
            
            # This week's performance
            'youtube_views_this_week': this_week_views,
            'youtube_growth_percentage': growth_estimate['estimated_growth_percentage'],
            'videos_published_this_week': len(this_week_videos),
            
            # Recent performance
            'recent_videos': recent_videos[:3],  # Top 3 recent videos
            'average_views_per_video': growth_estimate['recent_average_views'],
            
            # Metadata
            'last_updated': datetime.utcnow().isoformat(),
            'data_source': 'YouTube Data API v3'
        }
        
        return {
            "status": "success",
            "data": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.get("/search")
async def search_channel_videos(
    query: str = Query(..., description="Search query for videos"),
    max_results: int = Query(10, description="Number of results to return", ge=1, le=50)
):
    """Search for videos within the channel."""
    try:
        youtube_service = YouTubeDataAPIService()
        videos = youtube_service.search_channel_videos(query=query, max_results=max_results)
        
        return {
            "status": "success",
            "query": query,
            "data": videos,
            "count": len(videos)
        }
        
    except Exception as e:
        logger.error(f"Failed to search videos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")


@router.get("/weekly-performance")
async def get_weekly_performance():
    """Get this week's YouTube performance data for the main dashboard."""
    try:
        youtube_service = YouTubeDataAPIService()
        
        # Get recent videos and filter for this week
        recent_videos = youtube_service.get_recent_videos(max_results=20)
        
        from datetime import datetime, timedelta, timezone
        week_ago = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=7)
        
        # Calculate this week's metrics
        this_week_views = 0
        this_week_likes = 0
        this_week_comments = 0
        this_week_videos = 0
        
        for video in recent_videos:
            published_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
            if published_date >= week_ago:
                this_week_views += video['view_count']
                this_week_likes += video['like_count']
                this_week_comments += video['comment_count']
                this_week_videos += 1
        
        # Get growth estimate
        growth_data = youtube_service.get_channel_growth_estimate(days_back=7)
        
        return {
            "status": "success",
            "data": {
                "views_this_week": this_week_views,
                "likes_this_week": this_week_likes,
                "comments_this_week": this_week_comments,
                "videos_this_week": this_week_videos,
                "growth_percentage": growth_data['estimated_growth_percentage'],
                "average_views_per_video": this_week_views // this_week_videos if this_week_videos > 0 else 0,
                "period": "Last 7 days",
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get weekly performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get weekly data: {str(e)}")


@router.get("/top-videos")
async def get_top_performing_videos(
    max_results: int = Query(10, description="Number of top videos to return", ge=1, le=50),
    sort_by: str = Query("views", description="Sort by: views, likes, comments", regex="^(views|likes|comments)$")
):
    """Get top performing videos sorted by specified metric."""
    try:
        youtube_service = YouTubeDataAPIService()
        videos = youtube_service.get_recent_videos(max_results=max_results * 2)  # Get more to sort
        
        # Sort by the specified metric
        if sort_by == "views":
            videos.sort(key=lambda x: x['view_count'], reverse=True)
        elif sort_by == "likes":
            videos.sort(key=lambda x: x['like_count'], reverse=True)
        elif sort_by == "comments":
            videos.sort(key=lambda x: x['comment_count'], reverse=True)
        
        # Return top results
        top_videos = videos[:max_results]
        
        return {
            "status": "success",
            "sort_by": sort_by,
            "data": top_videos,
            "count": len(top_videos)
        }
        
    except Exception as e:
        logger.error(f"Failed to get top videos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get top videos: {str(e)}")
