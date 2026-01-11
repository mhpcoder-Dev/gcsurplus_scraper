"""
Quick test script to verify scheduler setup.

Run this to test the scheduler configuration:
    python test_scheduler.py
"""

import logging
from config import settings
from services.scheduler_service import SchedulerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_scheduler_configuration():
    """Test that scheduler configuration is valid"""
    logger.info("=" * 60)
    logger.info("Testing Scheduler Configuration")
    logger.info("=" * 60)
    
    # Check configuration
    logger.info(f"Scheduler Enabled: {settings.scheduler_enabled}")
    logger.info(f"Timezone: {settings.scheduler_timezone}")
    logger.info("")
    
    logger.info("Scraper Intervals (hours):")
    for site, interval in settings.scraper_intervals.items():
        logger.info(f"  - {site}: {interval}")
    logger.info("")
    
    if settings.scraper_schedule_times:
        logger.info("Scraper Schedule Times:")
        for site, times in settings.scraper_schedule_times.items():
            logger.info(f"  - {site}: {times}")
        logger.info("")
    
    # Create scheduler service
    try:
        scheduler = SchedulerService()
        logger.info("✓ SchedulerService created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create SchedulerService: {e}")
        return False
    
    # Add all sites
    try:
        scheduler.add_all_sites()
        logger.info("✓ All sites added successfully")
    except Exception as e:
        logger.error(f"✗ Failed to add sites: {e}")
        return False
    
    # Start the scheduler (required to get next run times)
    try:
        scheduler.start()
        logger.info("✓ Scheduler started successfully")
    except Exception as e:
        logger.error(f"✗ Failed to start scheduler: {e}")
        return False
    
    # Display scheduled jobs
    logger.info("")
    logger.info("Scheduled Jobs:")
    for job in scheduler.scheduler.get_jobs():
        logger.info(f"  • {job.name}")
        logger.info(f"    ID: {job.id}")
        logger.info(f"    Next run: {job.next_run_time}")
        logger.info("")
    
    # Stop the scheduler (cleanup for test)
    scheduler.stop()
    
    logger.info("=" * 60)
    logger.info("Scheduler Configuration Test: PASSED ✓")
    logger.info("=" * 60)
    logger.info("")
    logger.info("The scheduler is configured correctly!")
    logger.info("To start it with FastAPI, run: python main.py")
    logger.info("To run standalone, run: python scheduler.py")
    logger.info("")
    
    return True


if __name__ == "__main__":
    success = test_scheduler_configuration()
    exit(0 if success else 1)
