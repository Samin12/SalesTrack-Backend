"""
Scheduler service for running daily YouTube data synchronization jobs.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.daily_sync_service import DailySyncService
# GA4 service removed - using PostHog for analytics
from app.models.daily_sync import SyncConfiguration
from app.core.config import get_youtube_config

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled sync jobs."""
    
    def __init__(self):
        self.running = False
        self.sync_tasks: Dict[str, asyncio.Task] = {}
        
    async def start_scheduler(self):
        """Start the scheduler service."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting YouTube data sync scheduler...")
        
        # Start the main scheduler loop
        asyncio.create_task(self._scheduler_loop())
        
    async def stop_scheduler(self):
        """Stop the scheduler service."""
        if not self.running:
            return
        
        logger.info("Stopping YouTube data sync scheduler...")
        self.running = False
        
        # Cancel all running sync tasks
        for channel_id, task in self.sync_tasks.items():
            if not task.done():
                logger.info(f"Cancelling sync task for channel {channel_id}")
                task.cancel()
        
        self.sync_tasks.clear()
        
    async def _scheduler_loop(self):
        """Main scheduler loop that checks for sync jobs every hour."""
        while self.running:
            try:
                await self._check_and_run_syncs()
                
                # Wait for 1 hour before next check
                await asyncio.sleep(3600)  # 1 hour
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)
    
    async def _check_and_run_syncs(self):
        """Check all channels and run syncs if needed."""
        try:
            db = next(get_db())

            # Get all enabled sync configurations
            sync_configs = db.query(SyncConfiguration).filter(
                SyncConfiguration.sync_enabled == True
            ).all()

            logger.info(f"Checking {len(sync_configs)} channels for sync requirements")

            for config in sync_configs:
                try:
                    await self._check_channel_sync(db, config)
                except Exception as e:
                    logger.error(f"Error checking sync for channel {config.channel_id}: {e}")

            # Run GA4 data sync every 4 hours (every 4th scheduler loop)
            current_hour = datetime.now().hour
            if current_hour % 4 == 0:
                try:
                    logger.info("Running scheduled GA4 data sync")
                    await self._run_ga4_sync()
                except Exception as e:
                    logger.error(f"Error running GA4 sync: {e}")

            db.close()

        except Exception as e:
            logger.error(f"Error checking syncs: {e}")
    
    async def _check_channel_sync(self, db: Session, config: SyncConfiguration):
        """Check if a specific channel needs sync and run it if needed."""
        channel_id = config.channel_id
        
        # Skip if sync is already running for this channel
        if channel_id in self.sync_tasks and not self.sync_tasks[channel_id].done():
            logger.debug(f"Sync already running for channel {channel_id}")
            return
        
        # Check if sync is needed
        sync_service = DailySyncService(db)
        is_sync_needed = await sync_service.check_sync_needed(channel_id)
        
        if is_sync_needed:
            logger.info(f"Starting scheduled sync for channel {channel_id}")
            
            # Start sync task
            sync_task = asyncio.create_task(
                self._run_channel_sync(channel_id, "Scheduled sync")
            )
            self.sync_tasks[channel_id] = sync_task
        else:
            logger.debug(f"Sync not needed for channel {channel_id}")
    
    async def _run_channel_sync(self, channel_id: str, reason: str):
        """Run sync for a specific channel."""
        try:
            db = next(get_db())
            sync_service = DailySyncService(db)
            
            sync_id = await sync_service.start_sync(
                channel_id=channel_id,
                force=False,
                reason=reason
            )
            
            logger.info(f"Scheduled sync started for channel {channel_id}, sync_id: {sync_id}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error running scheduled sync for channel {channel_id}: {e}")
        finally:
            # Clean up task reference
            if channel_id in self.sync_tasks:
                del self.sync_tasks[channel_id]

    # GA4 sync removed - using PostHog for analytics
    
    async def trigger_manual_sync(self, channel_id: str, force: bool = False) -> str:
        """Manually trigger a sync for a specific channel."""
        try:
            db = next(get_db())
            sync_service = DailySyncService(db)
            
            sync_id = await sync_service.start_sync(
                channel_id=channel_id,
                force=force,
                reason="Manual trigger"
            )
            
            logger.info(f"Manual sync triggered for channel {channel_id}, sync_id: {sync_id}")
            
            db.close()
            return sync_id
            
        except Exception as e:
            logger.error(f"Error triggering manual sync for channel {channel_id}: {e}")
            raise
    
    def get_sync_status(self) -> Dict[str, any]:
        """Get current status of the scheduler and running syncs."""
        running_syncs = []
        
        for channel_id, task in self.sync_tasks.items():
            if not task.done():
                running_syncs.append({
                    "channel_id": channel_id,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc)  # Approximate
                })
        
        return {
            "scheduler_running": self.running,
            "running_syncs": running_syncs,
            "total_running_syncs": len(running_syncs)
        }


# Global scheduler instance
scheduler_service = SchedulerService()


async def start_scheduler():
    """Start the global scheduler service."""
    await scheduler_service.start_scheduler()


async def stop_scheduler():
    """Stop the global scheduler service."""
    await scheduler_service.stop_scheduler()


def get_scheduler() -> SchedulerService:
    """Get the global scheduler service instance."""
    return scheduler_service
