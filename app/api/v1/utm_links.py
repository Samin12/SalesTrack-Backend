"""
UTM Link tracking API endpoints for video-driven traffic analytics.
"""
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.utm_service import UTMService
from app.services.ga4_service import ga4_service  # Keep for migration period
from app.services.posthog_service import posthog_service
from app.models.utm_link import UTMLink
from app.api.v1.utm_schemas import (
    UTMLinkCreate,
    UTMLinkResponse,
    LinkClickCreate,
    LinkClickResponse,
    LinkAnalyticsResponse,
    VideoLinkPerformanceResponse,
    VideoTrafficCorrelationResponse,
    UTMLinksListResponse,
    VideoTrafficCorrelationListResponse
)

router = APIRouter()


@router.post("/utm-links", response_model=UTMLinkResponse, status_code=201)
async def create_utm_link(
    utm_link_data: UTMLinkCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new UTM tracking link for a YouTube video.

    This endpoint generates a trackable URL with UTM parameters that can be used
    in video descriptions, comments, or other promotional materials.

    PostHog tracking is recommended for enhanced analytics and privacy-first insights.
    """
    try:
        utm_service = UTMService(db)
        utm_link = utm_service.create_utm_link(
            video_id=utm_link_data.video_id,
            destination_url=utm_link_data.destination_url,
            utm_content=utm_link_data.utm_content,
            utm_term=utm_link_data.utm_term,
            tracking_type=utm_link_data.tracking_type
        )
        return utm_link
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create UTM link: {str(e)}")


@router.get("/utm-links", response_model=UTMLinksListResponse)
async def get_utm_links(
    video_id: Optional[str] = Query(None, description="Filter by video ID"),
    active_only: bool = Query(True, description="Show only active links"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of links to return"),
    offset: int = Query(0, ge=0, description="Number of links to skip"),
    db: Session = Depends(get_db)
):
    """
    Get UTM tracking links with optional filtering.
    
    Returns a list of UTM links with their tracking URLs and basic metadata.
    """
    try:
        utm_service = UTMService(db)
        links_with_stats = utm_service.get_utm_links_with_stats(
            video_id=video_id,
            active_only=active_only,
            limit=limit,
            offset=offset
        )

        return UTMLinksListResponse(
            timestamp=datetime.utcnow(),
            total_links=len(links_with_stats),
            links=links_with_stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve UTM links: {str(e)}")


@router.get("/utm-links/{link_id}/analytics", response_model=LinkAnalyticsResponse)
async def get_link_analytics(
    link_id: int,
    days_back: int = Query(30, ge=1, le=365, description="Number of days to include in analytics"),
    db: Session = Depends(get_db)
):
    """
    Get detailed analytics for a specific UTM tracking link.
    
    Returns click data, daily trends, and performance metrics for the link.
    """
    try:
        utm_service = UTMService(db)
        analytics = utm_service.get_link_analytics(link_id, days_back)
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve link analytics: {str(e)}")


@router.post("/utm-links/{link_id}/click", response_model=LinkClickResponse, status_code=201)
async def record_link_click(
    link_id: int,
    request: Request,
    click_data: Optional[LinkClickCreate] = None,
    db: Session = Depends(get_db)
):
    """
    Record a click event for a UTM tracking link.
    
    This endpoint is typically called when a user clicks on a tracked link.
    It captures metadata about the click for analytics purposes.
    """
    try:
        utm_service = UTMService(db)
        
        # Extract request metadata if not provided
        user_agent = None
        ip_address = None
        referrer = None
        
        if click_data:
            user_agent = click_data.user_agent
            ip_address = click_data.ip_address
            referrer = click_data.referrer
        
        # Fallback to request headers
        if not user_agent:
            user_agent = request.headers.get("user-agent")
        if not ip_address:
            ip_address = request.client.host if request.client else None
        if not referrer:
            referrer = request.headers.get("referer")
        
        click = utm_service.record_click(
            utm_link_id=link_id,
            user_agent=user_agent,
            ip_address=ip_address,
            referrer=referrer
        )

        # Send event to PostHog if enabled
        try:
            utm_link = db.query(UTMLink).filter(UTMLink.id == link_id).first()
            if utm_link and utm_link.posthog_enabled:
                await posthog_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    referrer=referrer
                )
        except Exception as posthog_error:
            # Don't fail the request if PostHog tracking fails
            from loguru import logger
            logger.warning(f"PostHog event tracking failed for link {link_id}: {posthog_error}")

        # Legacy GA4 tracking (keeping for migration period)
        try:
            if utm_link and utm_link.ga4_enabled:
                await ga4_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    referrer=referrer
                )
        except Exception as ga4_error:
            # Don't fail the request if GA4 tracking fails
            from loguru import logger
            logger.warning(f"GA4 event tracking failed for link {link_id}: {ga4_error}")

        return click
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record click: {str(e)}")


@router.get("/videos/{video_id}/link-performance", response_model=VideoLinkPerformanceResponse)
async def get_video_link_performance(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    Get link performance data for a specific YouTube video.
    
    Returns all UTM links associated with the video and their performance metrics,
    including click-through rates and conversion data.
    """
    try:
        utm_service = UTMService(db)
        performance = utm_service.get_video_link_performance(video_id)
        return performance
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve video link performance: {str(e)}")


@router.get("/analytics/video-traffic-correlation", response_model=VideoTrafficCorrelationListResponse)
async def get_video_traffic_correlation(
    days_back: int = Query(30, ge=1, le=365, description="Number of days to include in correlation analysis"),
    db: Session = Depends(get_db)
):
    """
    Get correlation data between video views and link clicks.
    
    Returns analytics showing how video performance correlates with link click-through rates,
    helping identify which types of content drive the most traffic.
    """
    try:
        utm_service = UTMService(db)
        correlation_data = utm_service.get_video_traffic_correlation(days_back)
        
        return VideoTrafficCorrelationListResponse(
            timestamp=datetime.utcnow(),
            total_videos=len(correlation_data),
            correlation_data=correlation_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve correlation data: {str(e)}")


# Redirect endpoint for UTM links (optional - for direct link handling)
@router.get("/r/{link_id}")
async def redirect_utm_link(
    link_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Redirect endpoint for UTM tracking links.
    
    This endpoint can be used to create shorter URLs that redirect to the destination
    while recording click analytics. Usage: /api/v1/r/{link_id}
    """
    try:
        from fastapi.responses import RedirectResponse
        
        utm_service = UTMService(db)

        # Get the specific UTM link by ID
        utm_link = db.query(UTMLink).filter(UTMLink.id == link_id, UTMLink.is_active == 1).first()

        if not utm_link:
            raise HTTPException(status_code=404, detail="UTM link not found")
        
        # Record the click
        utm_service.record_click(
            utm_link_id=link_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            referrer=request.headers.get("referer")
        )

        # Send event to PostHog if enabled
        try:
            if utm_link.posthog_enabled:
                await posthog_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None,
                    referrer=request.headers.get("referer")
                )
        except Exception as posthog_error:
            # Don't fail the request if PostHog tracking fails
            from loguru import logger
            logger.warning(f"PostHog event tracking failed for link {link_id}: {posthog_error}")

        # Legacy GA4 tracking (keeping for migration period)
        try:
            if utm_link.ga4_enabled:
                await ga4_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None,
                    referrer=request.headers.get("referer")
                )
        except Exception as ga4_error:
            # Don't fail the request if GA4 tracking fails
            from loguru import logger
            logger.warning(f"GA4 event tracking failed for link {link_id}: {ga4_error}")

        # For direct GA4 links, redirect to the direct URL with UTM parameters
        # For server redirect links, redirect to the destination URL
        if utm_link.tracking_type == 'direct_ga4':
            redirect_url = utm_link.direct_url
        else:
            redirect_url = utm_link.destination_url

        return RedirectResponse(url=redirect_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to redirect: {str(e)}")


@router.get("/track/{link_id}")
async def track_direct_ga4_click(
    link_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Fast tracking endpoint specifically for Direct GA4 links.
    Logs the click and redirects to destination with UTM parameters.
    """
    try:
        from fastapi.responses import RedirectResponse

        utm_service = UTMService(db)

        # Get the specific UTM link by ID
        utm_link = db.query(UTMLink).filter(UTMLink.id == link_id, UTMLink.is_active == 1).first()

        if not utm_link:
            raise HTTPException(status_code=404, detail="UTM link not found")

        # Only handle direct GA4 links through this endpoint
        if utm_link.tracking_type != 'direct_ga4':
            # Redirect to regular tracking endpoint for server redirect links
            return RedirectResponse(url=f"/api/v1/r/{link_id}", status_code=302)

        # Record the click (fast database operation)
        utm_service.record_click(
            utm_link_id=link_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            referrer=request.headers.get("referer")
        )

        # Send event to PostHog if enabled
        try:
            if utm_link.posthog_enabled:
                await posthog_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None,
                    referrer=request.headers.get("referer")
                )
        except Exception as posthog_error:
            # Don't fail the request if PostHog tracking fails
            from loguru import logger
            logger.warning(f"PostHog event tracking failed for link {link_id}: {posthog_error}")

        # Legacy GA4 tracking (keeping for migration period)
        try:
            if utm_link.ga4_enabled:
                await ga4_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None,
                    referrer=request.headers.get("referer")
                )
        except Exception as ga4_error:
            # Don't fail the request if GA4 tracking fails
            from loguru import logger
            logger.warning(f"GA4 event tracking failed for link {link_id}: {ga4_error}")

        # Redirect to destination with UTM parameters
        return RedirectResponse(url=utm_link.direct_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track direct GA4 click: {str(e)}")


@router.get("/go/{slug}")
async def redirect_pretty_utm_link(
    slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Redirect to the destination URL using pretty slug and track the click.
    This endpoint provides user-friendly URLs like /go/bookedin-product
    """
    try:
        from fastapi.responses import RedirectResponse

        utm_service = UTMService(db)

        # Get the UTM link by pretty slug
        utm_link = db.query(UTMLink).filter(
            UTMLink.pretty_slug == slug,
            UTMLink.is_active == 1
        ).first()

        if not utm_link:
            raise HTTPException(status_code=404, detail="Link not found")

        # Record the click
        utm_service.record_click(
            utm_link_id=utm_link.id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            referrer=request.headers.get("referer")
        )

        # Send event to PostHog if enabled
        try:
            if utm_link.posthog_enabled:
                await posthog_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None,
                    referrer=request.headers.get("referer")
                )
        except Exception as posthog_error:
            # Don't fail the request if PostHog tracking fails
            from loguru import logger
            logger.warning(f"PostHog event tracking failed for link {utm_link.id}: {posthog_error}")

        # Legacy GA4 tracking (keeping for migration period)
        try:
            if utm_link.ga4_enabled:
                await ga4_service.send_utm_click_event(
                    utm_link=utm_link,
                    user_agent=request.headers.get("user-agent"),
                    ip_address=request.client.host if request.client else None,
                    referrer=request.headers.get("referer")
                )
        except Exception as ga4_error:
            # Don't fail the request if GA4 tracking fails
            from loguru import logger
            logger.warning(f"GA4 event tracking failed for link {utm_link.id}: {ga4_error}")

        # Redirect based on tracking type
        if utm_link.tracking_type in ['direct_posthog', 'direct_ga4']:
            # For Direct PostHog/GA4, redirect to destination with UTM parameters
            redirect_url = utm_link.direct_url or utm_link.tracking_url
        else:
            # For Server Redirect, redirect to destination URL
            redirect_url = utm_link.destination_url

        return RedirectResponse(url=redirect_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to redirect: {str(e)}")


@router.delete("/utm-links/{link_id}")
async def delete_utm_link(
    link_id: int,
    db: Session = Depends(get_db)
):
    """Delete a UTM tracking link."""
    try:
        utm_service = UTMService(db)
        success = utm_service.delete_utm_link(link_id)

        if not success:
            raise HTTPException(status_code=404, detail="UTM link not found")

        return {
            "success": True,
            "message": "UTM link deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting UTM link {link_id}: {str(e)}")


# Google Analytics 4 Integration Endpoints

@router.post("/utm-links/{link_id}/ga4/enable")
async def enable_ga4_tracking(
    link_id: int,
    db: Session = Depends(get_db)
):
    """Enable Google Analytics 4 tracking for a UTM link."""
    try:
        utm_link = db.query(UTMLink).filter(UTMLink.id == link_id).first()
        if not utm_link:
            raise HTTPException(status_code=404, detail="UTM link not found")

        utm_link.ga4_enabled = True
        db.commit()

        return {
            "success": True,
            "message": "GA4 tracking enabled",
            "link_id": link_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable GA4 tracking: {str(e)}")


@router.post("/utm-links/{link_id}/ga4/disable")
async def disable_ga4_tracking(
    link_id: int,
    db: Session = Depends(get_db)
):
    """Disable Google Analytics 4 tracking for a UTM link."""
    try:
        utm_link = db.query(UTMLink).filter(UTMLink.id == link_id).first()
        if not utm_link:
            raise HTTPException(status_code=404, detail="UTM link not found")

        utm_link.ga4_enabled = False
        db.commit()

        return {
            "success": True,
            "message": "GA4 tracking disabled",
            "link_id": link_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable GA4 tracking: {str(e)}")


@router.post("/ga4/sync")
async def sync_ga4_data(
    days_back: int = Query(7, description="Number of days to sync"),
    db: Session = Depends(get_db)
):
    """Manually trigger GA4 data sync to local database."""
    try:
        result = await ga4_service.sync_ga4_data_to_database(days_back=days_back)
        return {
            "success": True,
            "message": "GA4 data sync completed",
            "synced_records": result["synced"],
            "errors": result["errors"],
            "days_synced": days_back
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GA4 sync failed: {str(e)}")


@router.get("/ga4/status")
async def get_ga4_status():
    """Get Google Analytics 4 integration status."""
    try:
        from app.core.config import settings

        status = {
            "ga4_configured": bool(settings.GA4_PROPERTY_ID and settings.GA4_MEASUREMENT_ID),
            "measurement_protocol_enabled": bool(settings.GA4_MEASUREMENT_ID and settings.GA4_API_SECRET),
            "data_api_enabled": bool(settings.GA4_PROPERTY_ID and settings.GA4_SERVICE_ACCOUNT_PATH),
            "service_account_exists": bool(
                settings.GA4_SERVICE_ACCOUNT_PATH and
                os.path.exists(settings.GA4_SERVICE_ACCOUNT_PATH)
            ) if settings.GA4_SERVICE_ACCOUNT_PATH else False
        }

        return {
            "success": True,
            "ga4_status": status,
            "integration_ready": all([
                status["measurement_protocol_enabled"],
                status["data_api_enabled"],
                status["service_account_exists"]
            ])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get GA4 status: {str(e)}")
