"""
PostHog API endpoints for managing PostHog integration and analytics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import logging

from app.core.database import get_db
from app.api.v1.schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_posthog_status(db: Session = Depends(get_db)):
    """Get PostHog integration status."""
    try:
        from app.services.posthog_service import posthog_service
        
        if not posthog_service:
            return {
                "posthog_status": {
                    "posthog_configured": False,
                    "api_key_valid": False,
                    "last_sync": None,
                    "total_events": 0,
                    "message": "PostHog service not configured"
                }
            }
        
        # Check if PostHog is properly configured
        configured = bool(posthog_service.api_key and posthog_service.project_id)
        
        # Try to validate API key by making a simple request
        api_key_valid = False
        if configured:
            try:
                # Test the API key with a simple request
                test_data = await posthog_service.get_website_analytics(days=1)
                api_key_valid = test_data is not None and "error" not in test_data
            except Exception as e:
                logger.warning(f"PostHog API key validation failed: {e}")
                api_key_valid = False
        
        # Get sync statistics from database
        from app.models.utm_link import UTMLink
        total_events = db.query(UTMLink).filter(UTMLink.posthog_enabled == True).count()
        
        # Get last sync time (approximate from UTM links with PostHog data)
        last_sync_link = db.query(UTMLink).filter(
            UTMLink.posthog_enabled == True,
            UTMLink.posthog_last_sync.isnot(None)
        ).order_by(UTMLink.posthog_last_sync.desc()).first()
        
        last_sync = last_sync_link.posthog_last_sync.isoformat() if last_sync_link and last_sync_link.posthog_last_sync else None
        
        return {
            "posthog_status": {
                "posthog_configured": configured,
                "api_key_valid": api_key_valid,
                "last_sync": last_sync,
                "total_events": total_events,
                "message": "PostHog integration active" if configured and api_key_valid else "PostHog not properly configured"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get PostHog status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PostHog status: {str(e)}")


@router.post("/sync")
async def trigger_posthog_sync(
    days_back: int = Query(7, description="Number of days to sync data for"),
    db: Session = Depends(get_db)
):
    """Trigger PostHog data synchronization."""
    try:
        from app.services.posthog_service import posthog_service
        
        if not posthog_service:
            raise HTTPException(status_code=400, detail="PostHog service not configured")
        
        # Trigger sync for UTM links
        result = await posthog_service.sync_utm_data(days_back=days_back)
        
        return {
            "synced": result.get("synced", 0),
            "errors": result.get("errors", 0),
            "message": f"PostHog sync completed for last {days_back} days"
        }
        
    except Exception as e:
        logger.error(f"PostHog sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"PostHog sync failed: {str(e)}")


@router.get("/analytics")
async def get_posthog_analytics(
    days: int = Query(7, description="Number of days to fetch analytics for"),
    db: Session = Depends(get_db)
):
    """Get PostHog analytics data."""
    try:
        from app.services.posthog_service import posthog_service
        
        if not posthog_service:
            return {
                "status": "error",
                "message": "PostHog service not configured",
                "analytics": {
                    "total_visits": 0,
                    "unique_visitors": 0,
                    "page_views": 0,
                    "daily_visits": [],
                    "top_pages": []
                }
            }
        
        # Get website analytics from PostHog
        analytics_data = await posthog_service.get_website_analytics(days=days)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "period_days": days,
            "analytics": analytics_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get PostHog analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PostHog analytics: {str(e)}")


@router.get("/health")
async def get_posthog_health():
    """Check PostHog service health."""
    try:
        from app.services.posthog_service import posthog_service
        
        if not posthog_service:
            return {
                "status": "not_configured",
                "message": "PostHog service not configured",
                "timestamp": datetime.now().isoformat()
            }
        
        # Test API connectivity
        try:
            test_data = await posthog_service.get_website_analytics(days=1)
            if test_data and "error" not in test_data:
                return {
                    "status": "healthy",
                    "message": "PostHog API responding",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "PostHog API not responding properly",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"PostHog API error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"PostHog health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
