"""
Conversion tracking API endpoints for PostHog integration.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.posthog_service import posthog_service
from app.models.traffic import ConversionEvent
from app.models.utm_link import UTMLink

router = APIRouter()


class ConversionEventCreate(BaseModel):
    """Schema for creating conversion events"""
    event_type: str  # signup, purchase, download, etc.
    event_value: float = 0.0
    utm_link_id: Optional[int] = None
    user_id: Optional[str] = None
    additional_properties: Optional[dict] = None


class ConversionEventResponse(BaseModel):
    """Schema for conversion event responses"""
    id: int
    event_type: str
    event_value: float
    date: datetime
    youtube_source: Optional[str]
    youtube_source_id: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    funnel_step: Optional[str]
    time_to_conversion: Optional[int]
    
    class Config:
        from_attributes = True


@router.post("/conversions", response_model=ConversionEventResponse, status_code=201)
async def track_conversion(
    conversion: ConversionEventCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Track a conversion event and send it to PostHog.
    
    This endpoint:
    1. Records the conversion in the local database
    2. Sends the conversion event to PostHog
    3. Associates it with UTM link if provided
    """
    try:
        # Get UTM link if provided
        utm_link = None
        if conversion.utm_link_id:
            utm_link = db.query(UTMLink).filter(UTMLink.id == conversion.utm_link_id).first()
            if not utm_link:
                raise HTTPException(status_code=404, detail="UTM link not found")
        
        # Create conversion event in database
        conversion_event = ConversionEvent(
            date=datetime.utcnow(),
            event_type=conversion.event_type,
            event_value=conversion.event_value,
            youtube_source=utm_link.utm_source if utm_link else None,
            youtube_source_id=utm_link.video_id if utm_link else None,
            user_id=conversion.user_id,
            session_id=request.headers.get("x-session-id"),
            funnel_step="conversion",
            time_to_conversion=None,  # Could be calculated based on first UTM click
            conversion_data=str(conversion.additional_properties) if conversion.additional_properties else None,
            data_source="posthog"
        )
        
        db.add(conversion_event)
        db.commit()
        db.refresh(conversion_event)
        
        # Send event to PostHog
        try:
            await posthog_service.send_conversion_event(
                event_type=conversion.event_type,
                event_value=conversion.event_value,
                utm_link=utm_link,
                user_id=conversion.user_id,
                additional_properties=conversion.additional_properties
            )
        except Exception as posthog_error:
            # Don't fail the request if PostHog tracking fails
            from loguru import logger
            logger.warning(f"PostHog conversion tracking failed: {posthog_error}")
        
        return conversion_event
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track conversion: {str(e)}")


@router.get("/conversions", response_model=List[ConversionEventResponse])
async def get_conversions(
    event_type: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get conversion events with optional filtering.
    """
    try:
        query = db.query(ConversionEvent)
        
        # Filter by event type if provided
        if event_type:
            query = query.filter(ConversionEvent.event_type == event_type)
        
        # Filter by date range
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(ConversionEvent.date >= start_date)
        
        # Order by most recent first
        conversions = query.order_by(ConversionEvent.date.desc()).limit(100).all()
        
        return conversions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversions: {str(e)}")


@router.get("/conversions/analytics")
async def get_conversion_analytics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get conversion analytics summary.
    """
    try:
        from datetime import timedelta
        from sqlalchemy import func
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get conversion summary
        conversion_summary = db.query(
            ConversionEvent.event_type,
            func.count(ConversionEvent.id).label('count'),
            func.sum(ConversionEvent.event_value).label('total_value'),
            func.avg(ConversionEvent.event_value).label('avg_value')
        ).filter(
            ConversionEvent.date >= start_date
        ).group_by(ConversionEvent.event_type).all()
        
        # Get source breakdown
        source_breakdown = db.query(
            ConversionEvent.youtube_source,
            func.count(ConversionEvent.id).label('count'),
            func.sum(ConversionEvent.event_value).label('total_value')
        ).filter(
            ConversionEvent.date >= start_date,
            ConversionEvent.youtube_source.isnot(None)
        ).group_by(ConversionEvent.youtube_source).all()
        
        # Calculate totals
        total_conversions = sum(item.count for item in conversion_summary)
        total_value = sum(item.total_value or 0 for item in conversion_summary)
        
        return {
            "analysis_period_days": days,
            "total_conversions": total_conversions,
            "total_value": total_value,
            "average_value": total_value / total_conversions if total_conversions > 0 else 0,
            "conversion_types": [
                {
                    "event_type": item.event_type,
                    "count": item.count,
                    "total_value": item.total_value or 0,
                    "avg_value": item.avg_value or 0
                }
                for item in conversion_summary
            ],
            "source_breakdown": [
                {
                    "source": item.youtube_source,
                    "count": item.count,
                    "total_value": item.total_value or 0
                }
                for item in source_breakdown
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversion analytics: {str(e)}")


@router.post("/conversions/bulk", status_code=201)
async def track_bulk_conversions(
    conversions: List[ConversionEventCreate],
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Track multiple conversion events in bulk.
    """
    try:
        created_conversions = []
        
        for conversion in conversions:
            # Get UTM link if provided
            utm_link = None
            if conversion.utm_link_id:
                utm_link = db.query(UTMLink).filter(UTMLink.id == conversion.utm_link_id).first()
            
            # Create conversion event
            conversion_event = ConversionEvent(
                date=datetime.utcnow(),
                event_type=conversion.event_type,
                event_value=conversion.event_value,
                youtube_source=utm_link.utm_source if utm_link else None,
                youtube_source_id=utm_link.video_id if utm_link else None,
                user_id=conversion.user_id,
                session_id=request.headers.get("x-session-id"),
                funnel_step="conversion",
                conversion_data=str(conversion.additional_properties) if conversion.additional_properties else None,
                data_source="posthog"
            )
            
            db.add(conversion_event)
            created_conversions.append(conversion_event)
            
            # Send to PostHog (async, don't wait)
            try:
                await posthog_service.send_conversion_event(
                    event_type=conversion.event_type,
                    event_value=conversion.event_value,
                    utm_link=utm_link,
                    user_id=conversion.user_id,
                    additional_properties=conversion.additional_properties
                )
            except Exception as posthog_error:
                from loguru import logger
                logger.warning(f"PostHog bulk conversion tracking failed: {posthog_error}")
        
        db.commit()
        
        return {
            "message": f"Successfully tracked {len(created_conversions)} conversions",
            "count": len(created_conversions)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track bulk conversions: {str(e)}")
