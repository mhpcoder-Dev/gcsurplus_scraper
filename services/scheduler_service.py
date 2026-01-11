"""
Scheduler Service - Manages scheduled scraping of multiple auction sources.

Features:
- Per-site configurable scraping intervals
- Support for both interval-based (every N hours) and time-based scheduling
- Automatic error handling and logging
- Job monitoring and status tracking
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_SUBMITTED
import pytz

from config import settings
from services.auction_service import AuctionService
from core.database import SessionLocal
from scrapers import GCSurplusScraper, GSAScraper, TreasuryScraper

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Manages scheduled scraping for multiple auction sources.
    Each source (gcsurplus, gsa, treasury) can have its own interval.
    """
    
    # Map of scraper names to scraper classes
    SCRAPERS = {
        'gcsurplus': GCSurplusScraper,
        'gsa': GSAScraper,
        'treasury': TreasuryScraper,
    }
    
    def __init__(self):
        """Initialize scheduler service"""
        self.timezone = settings.scheduler_timezone
        try:
            pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{self.timezone}', falling back to UTC")
            self.timezone = "UTC"
        
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)
        self.job_status: Dict[str, Dict] = {}  # Track job status
        self._setup_listeners()
    
    def _setup_listeners(self):
        """Setup event listeners for job monitoring"""
        self.scheduler.add_listener(
            self._job_submitted_listener,
            EVENT_JOB_SUBMITTED
        )
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
    
    def _job_submitted_listener(self, event):
        """Log job submission"""
        logger.debug(f"Job {event.job_id} submitted")
    
    def _job_executed_listener(self, event):
        """Log successful job execution"""
        logger.info(
            f"✓ Job '{event.job_id}' executed successfully at "
            f"{datetime.now(pytz.timezone(self.timezone)).strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )
        # Update job status
        if event.job_id in self.job_status:
            self.job_status[event.job_id]['last_run'] = datetime.now(pytz.timezone(self.timezone))
            self.job_status[event.job_id]['status'] = 'success'
    
    def _job_error_listener(self, event):
        """Log job errors"""
        logger.error(
            f"✗ Job '{event.job_id}' failed at "
            f"{datetime.now(pytz.timezone(self.timezone)).strftime('%Y-%m-%d %H:%M:%S %Z')}: {event.exception}"
        )
        # Update job status
        if event.job_id in self.job_status:
            self.job_status[event.job_id]['last_run'] = datetime.now(pytz.timezone(self.timezone))
            self.job_status[event.job_id]['status'] = 'error'
            self.job_status[event.job_id]['error'] = str(event.exception)
    
    async def _run_scraper_job(self, site_name: str, scraper_class):
        """
        Run a single scraper job.
        
        Args:
            site_name: Name of the site (e.g., 'gcsurplus', 'gsa', 'treasury')
            scraper_class: The scraper class to instantiate and run
        """
        job_id = f"scrape_{site_name}"
        logger.info(f"Starting scrape job for {site_name}...")
        
        try:
            # Initialize scraper
            scraper = scraper_class()
            
            # Run scraper
            items = scraper.scrape_all()
            logger.info(f"Scraper for {site_name} returned {len(items)} items")
            
            # Store in database
            db = SessionLocal()
            try:
                service = AuctionService(db)
                saved_count = service.save_scraped_items(items)
                logger.info(f"Saved {saved_count} items from {site_name} to database")
            finally:
                db.close()
            
            return {
                'site': site_name,
                'items_scraped': len(items),
                'items_saved': saved_count,
                'timestamp': datetime.now(pytz.timezone(self.timezone))
            }
            
        except Exception as e:
            logger.error(f"Error scraping {site_name}: {str(e)}", exc_info=True)
            raise
    
    def add_site_job(self, site_name: str, interval_hours: Optional[int] = None, 
                     schedule_times: Optional[str] = None):
        """
        Add a scraping job for a specific site.
        
        Args:
            site_name: Name of the site ('gcsurplus', 'gsa', or 'treasury')
            interval_hours: Interval in hours (e.g., 24 for daily). If None, uses config.
            schedule_times: Cron-style schedule times (e.g., "02:00" or "01:00,13:00").
                          If provided, overrides interval_hours.
        """
        if site_name not in self.SCRAPERS:
            logger.error(f"Unknown site: {site_name}")
            return False
        
        job_id = f"scrape_{site_name}"
        
        # Remove existing job if any
        existing_job = self.scheduler.get_job(job_id)
        if existing_job:
            logger.info(f"Removing existing job for {site_name}")
            self.scheduler.remove_job(job_id)
        
        # Determine trigger
        scraper_class = self.SCRAPERS[site_name]
        
        if schedule_times:
            # Use specific times from configuration
            trigger = self._create_cron_trigger(schedule_times)
            logger.info(f"Added {site_name} with schedule times: {schedule_times}")
        else:
            # Use interval
            interval = interval_hours or settings.scraper_intervals.get(site_name, 24)
            trigger = IntervalTrigger(hours=interval, timezone=pytz.timezone(self.timezone))
            logger.info(f"Added {site_name} with interval: every {interval} hours")
        
        # Add job to scheduler
        self.scheduler.add_job(
            self._run_scraper_job,
            trigger,
            args=(site_name, scraper_class),
            id=job_id,
            name=f"Scrape {site_name.upper()}",
            replace_existing=True,
            misfire_grace_time=3600,  # Allow 1 hour grace time for missed jobs
        )
        
        # Initialize job status (next_run will be set when scheduler starts)
        self.job_status[job_id] = {
            'site': site_name,
            'status': 'scheduled',
            'last_run': None,
            'next_run': None,  # Will be updated when scheduler starts
        }
        
        return True
    
    def _create_cron_trigger(self, schedule_times: str) -> CronTrigger:
        """
        Create a CronTrigger from schedule times string.
        
        Args:
            schedule_times: Time string like "02:00" or "01:00,13:00"
            
        Returns:
            CronTrigger object
        """
        times = [t.strip() for t in schedule_times.split(',')]
        hours = []
        minutes = []
        
        for time_str in times:
            try:
                hour, minute = time_str.split(':')
                hours.append(int(hour))
                minutes.append(int(minute))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid time format: {time_str}, skipping")
        
        if not hours:
            # Fallback to daily at midnight
            return CronTrigger(hour=0, minute=0, timezone=pytz.timezone(self.timezone))
        
        # Create trigger that runs at specified times
        # If all times have same minute, use that; otherwise use all minutes
        minute_str = f"{minutes[0]}" if len(set(minutes)) == 1 else ",".join(map(str, set(minutes)))
        hour_str = ",".join(map(str, set(hours)))
        
        return CronTrigger(
            hour=hour_str,
            minute=minute_str,
            timezone=pytz.timezone(self.timezone)
        )
    
    def add_all_sites(self):
        """Add scraping jobs for all configured sites"""
        logger.info("Adding scraping jobs for all sites...")
        
        for site_name in self.SCRAPERS.keys():
            # Check for schedule times first, then fall back to interval
            schedule_times = settings.scraper_schedule_times.get(site_name)
            interval_hours = settings.scraper_intervals.get(site_name)
            
            self.add_site_job(site_name, interval_hours, schedule_times)
        
        logger.info(f"Scheduled {len(self.SCRAPERS)} scraping jobs")
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            logger.info("=" * 60)
            logger.info("Starting Auction Scraper Scheduler")
            logger.info("=" * 60)
            
            self.scheduler.start()
            
            # Update job status with next run times (now that scheduler is started)
            for job in self.scheduler.get_jobs():
                job_id = job.id
                if job_id in self.job_status:
                    self.job_status[job_id]['next_run'] = job.next_run_time
            
            # Log all scheduled jobs
            logger.info(f"Scheduled jobs: {len(self.scheduler.get_jobs())}")
            for job in self.scheduler.get_jobs():
                logger.info(f"  • {job.name} (ID: {job.id})")
                logger.info(f"    Next run: {job.next_run_time}")
            
            logger.info("=" * 60)
            
            # Run initial scrape if configured
            if settings.run_initial_scrape:
                logger.info("Running initial scrape for all sites...")
                self._run_initial_scrapes()
    
    def _run_initial_scrapes(self):
        """Run initial scrape for all sites on startup (non-blocking)"""
        from datetime import timedelta
        
        # Schedule immediate one-time scrapes for each site
        # Stagger them by a few seconds to avoid overwhelming the system
        delay = 0
        for site_name, scraper_class in self.SCRAPERS.items():
            self.scheduler.add_job(
                self._run_scraper_job,
                'date',
                run_date=datetime.now(pytz.timezone(self.timezone)) + timedelta(seconds=delay),
                args=(site_name, scraper_class),
                id=f"initial_scrape_{site_name}",
                name=f"Initial Scrape - {site_name.upper()}",
                misfire_grace_time=300
            )
            logger.info(f"  • Scheduled initial scrape for {site_name} (in {delay} seconds)")
            delay += 5  # Stagger by 5 seconds
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
    
    def get_next_run_time(self, site_name: str) -> Optional[datetime]:
        """Get the next scheduled run time for a site"""
        job_id = f"scrape_{site_name}"
        job = self.scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None
    
    def get_all_jobs_status(self) -> List[Dict]:
        """Get status of all scheduled jobs"""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'status': self.job_status.get(job.id, {}).get('status', 'unknown'),
                'last_run': self.job_status.get(job.id, {}).get('last_run'),
            }
            jobs_info.append(job_info)
        return jobs_info
    
    def pause_site(self, site_name: str):
        """Pause scraping for a specific site"""
        job_id = f"scrape_{site_name}"
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused scraping for {site_name}")
            return True
        return False
    
    def resume_site(self, site_name: str):
        """Resume scraping for a specific site"""
        job_id = f"scrape_{site_name}"
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed scraping for {site_name}")
            return True
        return False
    
    def run_site_now(self, site_name: str):
        """Trigger an immediate scrape for a specific site"""
        job_id = f"scrape_{site_name}"
        job = self.scheduler.get_job(job_id)
        if job:
            # Reschedule to run immediately
            self.scheduler.reschedule_job(
                job_id,
                trigger=IntervalTrigger(seconds=0, timezone=pytz.timezone(self.timezone))
            )
            logger.info(f"Triggered immediate scrape for {site_name}")
            return True
        return False
