"""
API endpoints for daily YouTube data synchronization management.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.core.database import get_db
from app.core.config import get_youtube_config
from app.models.daily_sync import DailyYouTubeSync, YouTubeDataSnapshot, SyncConfiguration
from app.services.daily_sync_service import DailySyncService
from app.api.v1.schemas import (
    SyncStatusResponse, SyncTriggerRequest, SyncTriggerResponse,
    DailyYouTubeSync as DailyYouTubeSyncSchema, BaseResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(db: Session = Depends(get_db)):
    """Get current sync status and information."""
    try:
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id", "UCzGcYErpBX4ldvv0l7MWLfw")
        
        # Get current running sync
        current_sync = db.query(DailyYouTubeSync).filter(
            and_(
                DailyYouTubeSync.channel_id == channel_id,
                DailyYouTubeSync.sync_status == "running"
            )
        ).first()
        
        # Get last successful sync
        last_successful_sync = db.query(DailyYouTubeSync).filter(
            and_(
                DailyYouTubeSync.channel_id == channel_id,
                DailyYouTubeSync.sync_status == "completed"
            )
        ).order_by(desc(DailyYouTubeSync.completed_at)).first()
        
        # Get sync configuration
        sync_config = db.query(SyncConfiguration).filter(
            SyncConfiguration.channel_id == channel_id
        ).first()
        
        if not sync_config:
            # Create default configuration
            sync_config = SyncConfiguration(
                channel_id=channel_id,
                sync_enabled=True,
                sync_frequency_hours=24
            )
            db.add(sync_config)
            db.commit()
        
        # Calculate next scheduled sync
        next_sync = datetime.now(timezone.utc) + timedelta(hours=sync_config.sync_frequency_hours)
        if last_successful_sync:
            next_sync = last_successful_sync.completed_at + timedelta(hours=sync_config.sync_frequency_hours)
        
        # Calculate data freshness
        data_freshness_hours = None
        if last_successful_sync:
            time_since_sync = datetime.now(timezone.utc) - last_successful_sync.completed_at
            data_freshness_hours = time_since_sync.total_seconds() / 3600
        
        # Check if sync is needed
        sync_service = DailySyncService(db)
        is_sync_needed = await sync_service.check_sync_needed(channel_id)
        
        return SyncStatusResponse(
            current_sync=current_sync,
            last_successful_sync=last_successful_sync,
            next_scheduled_sync=next_sync,
            sync_frequency_hours=sync_config.sync_frequency_hours,
            data_freshness_hours=data_freshness_hours,
            is_sync_needed=is_sync_needed
        )
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync status")


@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger a sync operation."""
    try:
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id", "UCzGcYErpBX4ldvv0l7MWLfw")
        
        sync_service = DailySyncService(db)
        
        # Check if sync is needed (unless forced)
        if not request.force_sync:
            is_needed = await sync_service.check_sync_needed(channel_id)
            if not is_needed:
                return SyncTriggerResponse(
                    sync_id="",
                    sync_status="cancelled",
                    message="Sync not needed - data is still fresh"
                )
        
        # Start sync
        sync_id = await sync_service.start_sync(
            channel_id=channel_id,
            force=request.force_sync,
            reason=request.reason or "Manual trigger"
        )
        
        return SyncTriggerResponse(
            sync_id=sync_id,
            sync_status="running",
            message="Sync started successfully"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger sync")


@router.get("/history")
async def get_sync_history(
    limit: int = 10,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get sync history for the channel."""
    try:
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id", "UCzGcYErpBX4ldvv0l7MWLfw")
        
        query = db.query(DailyYouTubeSync).filter(
            DailyYouTubeSync.channel_id == channel_id
        )
        
        if status:
            query = query.filter(DailyYouTubeSync.sync_status == status)
        
        syncs = query.order_by(desc(DailyYouTubeSync.started_at)).limit(limit).all()
        
        return {
            "status": "success",
            "syncs": syncs,
            "total_count": len(syncs)
        }
        
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync history")


@router.get("/configuration")
async def get_sync_configuration(db: Session = Depends(get_db)):
    """Get sync configuration for the channel."""
    try:
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id", "UCzGcYErpBX4ldvv0l7MWLfw")
        
        config = db.query(SyncConfiguration).filter(
            SyncConfiguration.channel_id == channel_id
        ).first()
        
        if not config:
            # Create default configuration
            config = SyncConfiguration(
                channel_id=channel_id,
                sync_enabled=True,
                sync_frequency_hours=24
            )
            db.add(config)
            db.commit()
        
        return {
            "status": "success",
            "configuration": config
        }
        
    except Exception as e:
        logger.error(f"Error getting sync configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync configuration")


@router.put("/configuration")
async def update_sync_configuration(
    sync_enabled: bool = True,
    sync_frequency_hours: int = 24,
    max_retries: int = 3,
    db: Session = Depends(get_db)
):
    """Update sync configuration for the channel."""
    try:
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id", "UCzGcYErpBX4ldvv0l7MWLfw")
        
        config = db.query(SyncConfiguration).filter(
            SyncConfiguration.channel_id == channel_id
        ).first()
        
        if not config:
            config = SyncConfiguration(channel_id=channel_id)
            db.add(config)
        
        config.sync_enabled = sync_enabled
        config.sync_frequency_hours = sync_frequency_hours
        config.max_retries = max_retries
        config.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Sync configuration updated successfully",
            "configuration": config
        }
        
    except Exception as e:
        logger.error(f"Error updating sync configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to update sync configuration")


@router.get("/data-freshness")
async def get_data_freshness(db: Session = Depends(get_db)):
    """Get information about data freshness and sync recommendations."""
    try:
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id", "UCzGcYErpBX4ldvv0l7MWLfw")
        
        # Get last successful sync
        last_sync = db.query(DailyYouTubeSync).filter(
            and_(
                DailyYouTubeSync.channel_id == channel_id,
                DailyYouTubeSync.sync_status == "completed"
            )
        ).order_by(desc(DailyYouTubeSync.completed_at)).first()
        
        if not last_sync:
            return {
                "status": "success",
                "data_age_hours": None,
                "is_stale": True,
                "recommendation": "No sync found - initial sync required",
                "last_sync": None
            }
        
        # Calculate data age
        time_since_sync = datetime.now(timezone.utc) - last_sync.completed_at
        data_age_hours = time_since_sync.total_seconds() / 3600
        
        # Determine if data is stale (older than 25 hours to account for slight delays)
        is_stale = data_age_hours > 25
        
        recommendation = "Data is fresh"
        if is_stale:
            recommendation = "Data is stale - sync recommended"
        elif data_age_hours > 20:
            recommendation = "Data will be stale soon - sync will run automatically"
        
        return {
            "status": "success",
            "data_age_hours": round(data_age_hours, 2),
            "is_stale": is_stale,
            "recommendation": recommendation,
            "last_sync": {
                "sync_id": last_sync.sync_id,
                "completed_at": last_sync.completed_at,
                "videos_synced": last_sync.videos_synced,
                "api_calls_made": last_sync.api_calls_made
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting data freshness: {e}")
        raise HTTPException(status_code=500, detail="Failed to get data freshness")
