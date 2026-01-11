"""
Scheduler initialization and management.

This module provides the entry point for starting and managing the
auction scraper scheduler with site-specific configurations.
"""

import logging
import asyncio
from services.scheduler_service import SchedulerService
from config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: SchedulerService = None


def get_scheduler() -> SchedulerService:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def start_scheduler() -> SchedulerService:
    """
    Initialize and start the scheduler for all configured sites.
    
    Returns:
        SchedulerService instance
    """
    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled in configuration")
        return None
    
    scheduler = get_scheduler()
    
    # Add jobs for all configured sites
    scheduler.add_all_sites()
    
    # Start the scheduler
    scheduler.start()
    
    return scheduler


def stop_scheduler():
    """Stop the scheduler gracefully"""
    global _scheduler
    if _scheduler and _scheduler.scheduler.running:
        logger.info("Stopping scheduler...")
        _scheduler.stop()
        _scheduler = None


async def run_scheduler():
    """
    Run the scheduler indefinitely (for development/testing).
    This keeps the scheduler running even when not embedded in FastAPI.
    """
    scheduler = start_scheduler()
    
    if not scheduler:
        logger.error("Failed to start scheduler")
        return
    
    try:
        # Keep the scheduler running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        stop_scheduler()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run scheduler standalone
    asyncio.run(run_scheduler())
