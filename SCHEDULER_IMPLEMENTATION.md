# Multi-Site Scheduler Implementation Summary

## What Was Added

A production-ready scheduler for the gcsurplus-scraper that allows each auction source to have independent scraping intervals.

### Files Created/Modified

#### New Files
1. **`services/scheduler_service.py`** - Core scheduler service
   - Multi-site job scheduling
   - Per-site interval configuration
   - Cron-based time scheduling
   - Job monitoring and status tracking
   - Error handling and logging

2. **`SCHEDULER_CONFIG.md`** - Comprehensive configuration guide

#### Modified Files

1. **`config.py`** - Added scheduler settings
   ```python
   scheduler_enabled: bool = True
   scheduler_timezone: str = "UTC"
   scraper_intervals: Dict[str, int] = {
       "gcsurplus": 24,    # Every 24 hours
       "gsa": 12,          # Every 12 hours
       "treasury": 48      # Every 48 hours
   }
   scraper_schedule_times: Dict[str, str] = {}  # For specific times
   ```

2. **`scheduler.py`** - Complete rewrite with new service integration
   - `start_scheduler()` - Initialize and start all jobs
   - `stop_scheduler()` - Graceful shutdown
   - `get_scheduler()` - Access scheduler instance
   - `run_scheduler()` - Standalone mode for testing

3. **`main.py`** - Added scheduler startup/shutdown
   - Starts scheduler on FastAPI startup
   - Stops scheduler on FastAPI shutdown
   - Proper logging and error handling

4. **`services/auction_service.py`** - Added helper method
   - `save_scraped_items()` - Efficiently save pre-scraped items

## How It Works

### Architecture

```
FastAPI Startup
    ↓
Initialize Database
    ↓
Create SchedulerService
    ↓
Add Jobs for Each Site (with different intervals)
    ↓
Start APScheduler
    ↓
Background Jobs Run on Schedule
    ↓
Each Job:
  1. Scrapes data from site
  2. Saves to database
  3. Logs success/failure
  4. Re-schedules automatically
```

### Scheduling Methods

#### 1. Interval-Based (Default)
```python
# Every X hours
scraper_intervals = {
    "gcsurplus": 24,  # Daily
    "gsa": 12,        # Twice daily
    "treasury": 48,   # Every 2 days
}
```

#### 2. Time-Based (Specific Times)
```python
# At specific times
scraper_schedule_times = {
    "gcsurplus": "02:00",        # 2:00 AM
    "gsa": "01:00,13:00",        # 1:00 AM and 1:00 PM
    "treasury": "03:00",         # 3:00 AM
}
```

## Key Features

✅ **Per-Site Configuration** - Each auction source can have different intervals
✅ **Flexible Scheduling** - Both interval and cron-based scheduling
✅ **Job Monitoring** - Track execution status, last run, next run
✅ **Error Handling** - Comprehensive logging and error recovery
✅ **Graceful Shutdown** - Proper cleanup on application exit
✅ **Timezone Support** - Configurable timezone (UTC, EST, PST, etc.)
✅ **Easy Pause/Resume** - Manage individual site jobs
✅ **Standalone Mode** - Can run scheduler without FastAPI
✅ **Production Ready** - Error recovery, logging, grace periods

## Quick Start

### 1. Default Configuration (No Changes Needed)

The scheduler comes pre-configured and will work out of the box:
- GCSurplus: Every 24 hours
- GSA: Every 12 hours
- Treasury: Every 48 hours

### 2. Customize Intervals

Edit `config.py`:

```python
scraper_intervals: Dict[str, int] = {
    "gcsurplus": 24,    # Change to your preferred interval
    "gsa": 6,           # More frequent updates
    "treasury": 72,     # Less frequent
}
```

### 3. Use Specific Times

```python
scraper_schedule_times: Dict[str, str] = {
    "gcsurplus": "02:00",      # 2:00 AM
    "gsa": "01:00,13:00",      # 1:00 AM and 1:00 PM
    "treasury": "03:00",       # 3:00 AM
}
```

### 4. Set Timezone

Edit `.env`:
```env
SCHEDULER_TIMEZONE=America/New_York
# or any valid pytz timezone
```

## Usage Examples

### Check Job Status
```python
from scheduler import get_scheduler

scheduler = get_scheduler()
jobs = scheduler.get_all_jobs_status()
for job in jobs:
    print(f"{job['name']}: Next run at {job['next_run']}")
```

### Pause a Site
```python
from scheduler import get_scheduler
scheduler = get_scheduler()
scheduler.pause_site("gcsurplus")
```

### Resume a Site
```python
scheduler.resume_site("gcsurplus")
```

### Trigger Immediate Scrape
```python
scheduler.run_site_now("gsa")
```

### Get Next Run Time
```python
next_run = scheduler.get_next_run_time("treasury")
```

## Configuration Examples

### Heavy Scraping (Fresh Data)
```python
scraper_intervals = {
    "gcsurplus": 4,   # Every 4 hours (6x daily)
    "gsa": 2,         # Every 2 hours (12x daily)
    "treasury": 6,    # Every 6 hours (4x daily)
}
```

### Light Scraping (Low Load)
```python
scraper_intervals = {
    "gcsurplus": 48,  # Every 2 days
    "gsa": 24,        # Daily
    "treasury": 72,   # Every 3 days
}
```

### Staggered Times (Balanced)
```python
scraper_schedule_times = {
    "gcsurplus": "02:00",    # 2:00 AM
    "gsa": "02:15",          # 2:15 AM
    "treasury": "02:30",     # 2:30 AM
}
```

## Monitoring

### View Logs
The scheduler logs all events to the application logger:

```
2026-01-11 10:00:00,000 - services.scheduler_service - INFO - Starting scrape job for gcsurplus...
2026-01-11 10:00:15,000 - services.scheduler_service - INFO - ✓ Job 'scrape_gcsurplus' executed successfully
2026-01-11 10:12:00,000 - services.scheduler_service - INFO - Starting scrape job for gsa...
```

### Check Database

Query to see when items were last updated:

```sql
SELECT 
    source,
    COUNT(*) as total_items,
    MAX(updated_at) as last_update
FROM auction_items
GROUP BY source;
```

## Troubleshooting

### Scheduler Not Running
1. Check `SCHEDULER_ENABLED=true` in `.env`
2. Verify database connection works
3. Check application logs for errors
4. Ensure APScheduler is installed: `pip install apscheduler`

### Jobs Not Running at Expected Times
1. Verify `SCHEDULER_TIMEZONE` is set correctly
2. Check time format (should be `HH:MM` like `02:00`)
3. Look for error logs
4. Test with shorter intervals first

### High Database Load
1. Increase scraping intervals
2. Reduce number of sites
3. Check database connection pool settings
4. Implement job chaining

## File Structure

```
gcsurplus-scraper/
├── scheduler.py                    # Scheduler entry point
├── config.py                       # Scheduler configuration (updated)
├── main.py                         # FastAPI app (updated)
├── SCHEDULER_CONFIG.md             # Detailed configuration guide
│
├── services/
│   ├── scheduler_service.py        # Core scheduler logic (NEW)
│   └── auction_service.py          # Auction service (updated)
│
├── scrapers/
│   ├── base.py                     # Base scraper interface
│   ├── gcsurplus.py                # GCSurplus scraper
│   ├── gsa.py                      # GSA scraper
│   └── treasury.py                 # Treasury scraper
```

## Next Steps

1. Review `SCHEDULER_CONFIG.md` for detailed configuration options
2. Test the scheduler with: `python scheduler.py`
3. Customize intervals for your use case
4. Deploy and monitor job execution
5. Adjust intervals based on performance

## Dependencies

- `apscheduler>=3.10.0` (already in requirements.txt)
- `pytz` (for timezone support)
- `fastapi` (for integration)
- Python 3.8+

All dependencies are already included in `requirements.txt`.

## Production Recommendations

1. **Set specific times** instead of intervals for predictable behavior
2. **Stagger jobs** - don't run all sites at the same time
3. **Monitor database** - check connection pool and query performance
4. **Set appropriate intervals** - balance freshness with API rate limits
5. **Use production timezone** - match your deployment region
6. **Configure logging** - set `LOG_LEVEL=INFO` for debugging
7. **Test thoroughly** - verify jobs run at expected times before deploying

## Questions?

Refer to:
- `SCHEDULER_CONFIG.md` - Comprehensive configuration guide
- `services/scheduler_service.py` - Source code with documentation
- [APScheduler Docs](https://apscheduler.readthedocs.io/)
