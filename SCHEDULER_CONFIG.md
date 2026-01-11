## Scheduler Configuration Guide

This document explains how to configure the multi-site scheduler with different intervals for each auction source.

### Overview

The scheduler uses **APScheduler** to automatically scrape auctions from multiple sites at configurable intervals:
- **GCSurplus** (Canada): Default 24 hours
- **GSA** (US Federal): Default 12 hours  
- **Treasury** (US Real Estate): Default 48 hours

Each site can have its own schedule, allowing you to balance data freshness with API rate limits.

### Configuration

#### Basic Setup (.env)

```env
# Enable/disable the scheduler
SCHEDULER_ENABLED=true

# Timezone for scheduling (see pytz documentation for valid timezones)
SCHEDULER_TIMEZONE=UTC
```

#### Customizing Site Intervals

Edit `config.py` to modify scraping intervals:

```python
# In config.py - Pydantic Settings class
scraper_intervals: Dict[str, int] = {
    "gcsurplus": 24,    # Every 24 hours
    "gsa": 12,          # Every 12 hours (more active updates)
    "treasury": 48      # Every 48 hours (less frequent)
}
```

**Available sites:**
- `"gcsurplus"` - GCSurplus.ca Canadian government auctions
- `"gsa"` - GSA.gov US federal property auctions
- `"treasury"` - Treasury.gov US seized real estate auctions

#### Schedule by Specific Times

Instead of intervals, you can specify exact times:

```python
# In config.py
scraper_schedule_times: Dict[str, str] = {
    "gcsurplus": "02:00",           # Run at 2:00 AM UTC
    "gsa": "01:00,13:00",           # Run at 1:00 AM and 1:00 PM UTC
    "treasury": "03:00",            # Run at 3:00 AM UTC
}
```

**Note:** If both `scraper_intervals` and `scraper_schedule_times` are set, the schedule times take precedence.

### How It Works

#### Startup Sequence

1. FastAPI application starts
2. Database is initialized
3. `SchedulerService` is created and configured with all sites
4. Each site gets a separate scheduled job
5. Scheduler starts running in the background

#### Scheduled Execution

When a job runs:

```
1. Scraper.scrape_all() → Fetches data from source
2. AuctionService.save_scraped_items() → Saves to database
3. Event listeners log success/errors
4. Next run scheduled automatically
```

#### Error Handling

- Failed jobs are logged with full stack traces
- Job status is tracked (success, error, error message)
- Failed jobs don't prevent other jobs from running
- Grace period: 1 hour for missed jobs

### Monitoring the Scheduler

#### Check Job Status

The scheduler tracks all jobs and their status:

```python
from scheduler import get_scheduler

scheduler = get_scheduler()
jobs = scheduler.get_all_jobs_status()

# Output:
# [
#   {
#     'id': 'scrape_gcsurplus',
#     'name': 'Scrape GCSURPLUS',
#     'next_run': datetime(...),
#     'status': 'success',
#     'last_run': datetime(...)
#   },
#   ...
# ]
```

#### Get Next Run Time for a Site

```python
scheduler = get_scheduler()
next_run = scheduler.get_next_run_time("gcsurplus")
# Returns: datetime object or None
```

#### View Logs

The scheduler logs to the main application logger. Configure logging level in `.env`:

```env
LOG_LEVEL=INFO
```

**Log entries include:**
- `Starting scrape job for {site}...`
- `✓ Job '{job_id}' executed successfully`
- `✗ Job '{job_id}' failed with error: {error}`

### Managing Jobs

#### Pause/Resume a Specific Site

```python
from scheduler import get_scheduler

scheduler = get_scheduler()

# Pause scraping for GCSurplus
scheduler.pause_site("gcsurplus")

# Resume scraping
scheduler.resume_site("gcsurplus")
```

#### Trigger Immediate Scrape

```python
# Run immediately (useful for testing)
scheduler.run_site_now("gcsurplus")
```

#### Stop Scheduler

```python
from scheduler import stop_scheduler

stop_scheduler()
```

### Troubleshooting

#### Scheduler Not Starting

**Check:**
- `SCHEDULER_ENABLED=true` in `.env`
- Database connection is working
- APScheduler is installed: `pip install apscheduler`

#### Jobs Not Running at Expected Times

**Check:**
- Timezone is correctly set: `SCHEDULER_TIMEZONE` in `.env`
- Time format is correct: `HH:MM` or `HH:MM,HH:MM`
- Check logs for error messages
- Verify FastAPI application is running (scheduler runs in-process)

#### High Memory or Database Load

**Solution:**
- Increase scraping intervals (e.g., `"gcsurplus": 48`)
- Reduce the number of sites being scraped
- Implement job chaining to stagger job execution
- Configure database connection pooling

### Advanced Configuration

#### Environment Variable Overrides

You can override any setting via `.env`:

```env
SCRAPER_INTERVALS_GCSURPLUS=24
SCRAPER_INTERVALS_GSA=12
SCRAPER_INTERVALS_TREASURY=48
SCRAPER_SCHEDULE_TIMES_GCSURPLUS=02:00
SCRAPER_SCHEDULE_TIMES_GSA=01:00,13:00
```

#### Disable Specific Sites

To disable a site without removing the configuration:

```python
# Modify config.py - set interval to None or very large value
scraper_intervals: Dict[str, int] = {
    "gcsurplus": 24,
    "gsa": None,  # Will not be scheduled
    "treasury": 48
}
```

#### Custom Scraper Integration

To add a new scraper source:

1. Create scraper class in `scrapers/newsource.py` inheriting from `BaseScraper`
2. Add to `SchedulerService.SCRAPERS` dict:
   ```python
   SCRAPERS = {
       'gcsurplus': GCSurplusScraper,
       'gsa': GSAScraper,
       'treasury': TreasuryScraper,
       'newsource': NewSourceScraper,  # Add here
   }
   ```
3. Add interval in `config.py`:
   ```python
   scraper_intervals: Dict[str, int] = {
       "gcsurplus": 24,
       "gsa": 12,
       "treasury": 48,
       "newsource": 6,  # Your custom interval
   }
   ```

### Performance Tips

1. **Stagger Job Times**: Don't run all scrapers at the same time
   ```python
   scraper_schedule_times = {
       "gcsurplus": "02:00",    # 2:00 AM
       "gsa": "02:15",          # 2:15 AM
       "treasury": "02:30",     # 2:30 AM
   }
   ```

2. **Use Longer Intervals for Large Sources**: GSA has the most items
   ```python
   scraper_intervals = {
       "gcsurplus": 12,   # More frequent
       "gsa": 24,         # Less frequent (larger dataset)
       "treasury": 48,    # Less frequent
   }
   ```

3. **Monitor Database Performance**: Check query logs and optimize if needed

4. **Use Connection Pooling**: Configured in `config.py`
   ```python
   db_pool_size = 5          # Number of connections
   db_max_overflow = 10      # Additional temporary connections
   db_pool_pre_ping = True   # Test connections before use
   ```

### Testing the Scheduler

#### Test with Environment Variable

```env
# Test mode: run every 5 minutes instead of configured interval
TEST_EVERY_5_MINUTES=true
```

#### Test Standalone

Run the scheduler without FastAPI:

```bash
python scheduler.py
```

This will:
1. Load configuration
2. Create scheduler service
3. Add all sites
4. Start scheduler
5. Keep running until you press Ctrl+C

### Examples

#### Daily Scraping at 2 AM UTC

```env
# .env
SCHEDULER_TIMEZONE=UTC
```

```python
# config.py
scraper_intervals = {}  # Empty = use schedule_times
scraper_schedule_times = {
    "gcsurplus": "02:00",
    "gsa": "02:00",
    "treasury": "02:00",
}
```

#### Different Timezones

```env
# .env
SCHEDULER_TIMEZONE=America/New_York  # or any valid pytz timezone
```

```python
# config.py
scraper_schedule_times = {
    "gcsurplus": "02:00",  # 2:00 AM EST/EDT
    "gsa": "03:00",        # 3:00 AM EST/EDT
    "treasury": "04:00",   # 4:00 AM EST/EDT
}
```

#### Frequent Updates for Fresh Data

```python
# config.py
scraper_intervals = {
    "gcsurplus": 6,   # Every 6 hours (4x daily)
    "gsa": 4,         # Every 4 hours (6x daily)
    "treasury": 12,   # Every 12 hours (2x daily)
}
```

### See Also

- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Pytz Timezone List](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
- [FastAPI Application Lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [SchedulerService API](services/scheduler_service.py)
