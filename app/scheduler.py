from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime

from app.scraper import GCSurplusScraper
from app.database import SessionLocal
from app import crud
from app.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_scrape_job():
    """Run the scraping job"""
    logger.info(f"Starting scheduled scrape job at {datetime.utcnow()}")
    
    try:
        # Create scraper instance
        scraper = GCSurplusScraper()
        
        # Scrape all items
        items = scraper.scrape_all()
        logger.info(f"Scraped {len(items)} items")
        
        # Update database
        db = SessionLocal()
        try:
            current_lot_numbers = []
            
            for item_data in items:
                # Store current lot numbers
                current_lot_numbers.append(item_data['lot_number'])
                
                # Create or update item
                crud.create_or_update_item(db, item_data)
            
            # Mark items not in current scrape as unavailable
            if current_lot_numbers:
                crud.mark_items_as_unavailable(db, current_lot_numbers)
                logger.info("Marked missing items as unavailable")
            
            # Clean up old items (older than 30 days)
            deleted_count = crud.delete_old_items(db, days=30)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old items")
            
            logger.info("Scrape job completed successfully")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in scrape job: {e}", exc_info=True)


def start_scheduler():
    """Start the scheduler"""
    # Add job to run every X hours
    scheduler.add_job(
        run_scrape_job,
        trigger=IntervalTrigger(hours=settings.scrape_interval_hours),
        id='scrape_job',
        name='Scrape GCSurplus listings',
        replace_existing=True
    )
    
    # Run once on startup
    scheduler.add_job(
        run_scrape_job,
        id='initial_scrape',
        name='Initial scrape on startup'
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Will run every {settings.scrape_interval_hours} hours")


def stop_scheduler():
    """Stop the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
