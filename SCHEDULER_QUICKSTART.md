# Scheduler Quick Start Guide

## 5-Minute Setup

The scheduler is already integrated and will work immediately with default settings. Here's what happens:

### Default Configuration
- **GCSurplus**: Scrapes every 24 hours
- **GSA**: Scrapes every 12 hours (more active)
- **Treasury**: Scrapes every 48 hours

### To Use Default Configuration

Just run the application normally:

```bash
python main.py
# or
uvicorn main:app --reload
```

The scheduler will:
1. Start automatically on application startup
2. Run all three scrapers on their schedules
3. Log all activity to console/logs
4. Continue running in the background

**That's it!** No configuration needed.

---

## Customization (5 minutes)

### Change Scraping Intervals

Edit `config.py` and modify this section:

```python
scraper_intervals: Dict[str, int] = {
    "gcsurplus": 24,    # Change this number (in hours)
    "gsa": 12,          # Change this number
    "treasury": 48      # Change this number
}
```

Examples:
```python
# More frequent updates
scraper_intervals = {
    "gcsurplus": 6,     # Every 6 hours (4x daily)
    "gsa": 4,           # Every 4 hours (6x daily)
    "treasury": 12,     # Every 12 hours (2x daily)
}

# Less frequent (save bandwidth)
scraper_intervals = {
    "gcsurplus": 48,    # Every 2 days
    "gsa": 24,          # Daily
    "treasury": 72,     # Every 3 days
}
```

### Run at Specific Times

Instead of intervals, specify exact times:

```python
scraper_schedule_times: Dict[str, str] = {
    "gcsurplus": "02:00",        # Run at 2:00 AM
    "gsa": "01:00,13:00",        # Run at 1:00 AM and 1:00 PM
    "treasury": "03:00",         # Run at 3:00 AM
}
```

**Note:** When `scraper_schedule_times` is set, it takes priority over `scraper_intervals`.

### Set Timezone

Edit `.env`:
```env
SCHEDULER_TIMEZONE=America/New_York
```

Common timezones:
- `UTC` - Universal Time
- `America/New_York` - Eastern Time
- `America/Los_Angeles` - Pacific Time
- `America/Chicago` - Central Time
- `Europe/London` - UK Time
- `Europe/Paris` - Central European Time
- `Asia/Tokyo` - Japan Time
- `Australia/Sydney` - Australian Eastern Time

---

## Testing

### Test Standalone (Without FastAPI)

```bash
cd gcsurplus-scraper
python scheduler.py
```

Output:
```
2026-01-11 10:00:00 - INFO - ============================================================
2026-01-11 10:00:00 - INFO - Starting Auction Scraper Scheduler
2026-01-11 10:00:00 - INFO - ============================================================
2026-01-11 10:00:00 - INFO - Scheduled jobs: 3
2026-01-11 10:00:00 - INFO -   • Scrape GCSURPLUS (ID: scrape_gcsurplus)
2026-01-11 10:00:00 - INFO -     Next run: 2026-01-12 02:00:00+00:00
2026-01-11 10:00:00 - INFO -   • Scrape GSA (ID: scrape_gsa)
2026-01-11 10:00:00 - INFO -     Next run: 2026-01-11 14:00:00+00:00
2026-01-11 10:00:00 - INFO -   • Scrape TREASURY (ID: scrape_treasury)
2026-01-11 10:00:00 - INFO -     Next run: 2026-01-13 03:00:00+00:00
2026-01-11 10:00:00 - INFO - ============================================================
```

Press `Ctrl+C` to stop.

### Test with Short Intervals

For quick testing, temporarily change intervals to run every few minutes:

```python
# In config.py - temporarily for testing
scraper_intervals: Dict[str, int] = {
    "gcsurplus": 0.01,  # Every ~36 seconds
    "gsa": 0.02,        # Every ~1 minute
    "treasury": 0.03,   # Every ~2 minutes
}
```

---

## Monitoring

### Check Logs

Look for lines like:
```
✓ Job 'scrape_gcsurplus' executed successfully
✓ Job 'scrape_gsa' executed successfully
✓ Job 'scrape_treasury' executed successfully
```

### View Database

Check when items were last updated:

```sql
SELECT 
    source,
    COUNT(*) as total_items,
    MAX(updated_at) as last_update
FROM auction_items
GROUP BY source;
```

### Check Next Run Times in Code

```python
from scheduler import get_scheduler

scheduler = get_scheduler()

# Get all jobs
jobs = scheduler.get_all_jobs_status()
for job in jobs:
    print(f"{job['name']}: Next run at {job['next_run']}")

# Get specific site
next_run = scheduler.get_next_run_time("gcsurplus")
print(f"GCSurplus will next run at: {next_run}")
```

---

## Common Configurations

### Keep Everything Fresh
```python
scraper_intervals = {
    "gcsurplus": 4,
    "gsa": 2,
    "treasury": 6
}
```

### Minimize Load
```python
scraper_intervals = {
    "gcsurplus": 48,
    "gsa": 24,
    "treasury": 72
}
```

### Daily Scrape at 2 AM
```python
scraper_schedule_times = {
    "gcsurplus": "02:00",
    "gsa": "02:00",
    "treasury": "02:00"
}
```

### Staggered Daily Scrapes
```python
scraper_schedule_times = {
    "gcsurplus": "02:00",  # 2:00 AM
    "gsa": "02:15",        # 2:15 AM
    "treasury": "02:30"    # 2:30 AM
}
```

### Multiple Times Per Day (Balanced)
```python
scraper_schedule_times = {
    "gcsurplus": "02:00,14:00",      # 2:00 AM and 2:00 PM
    "gsa": "01:00,07:00,13:00,19:00", # Every 6 hours
    "treasury": "03:00,15:00"         # 3:00 AM and 3:00 PM
}
```

---

## Troubleshooting

### Jobs Not Running

**Check 1:** Is scheduler enabled?
```env
SCHEDULER_ENABLED=true
```

**Check 2:** Is the application running?
- The scheduler runs in-process with FastAPI
- It stops when the application stops
- It runs in the background (doesn't block API requests)

**Check 3:** Check the logs for errors
- Look for `ERROR` messages
- Check database connection
- Verify APScheduler is installed: `pip install apscheduler`

### Wrong Timezone

Check your `.env` file:
```env
SCHEDULER_TIMEZONE=UTC  # Wrong
SCHEDULER_TIMEZONE=America/New_York  # Correct
```

If you set `02:00` but it's running at the wrong time, it's likely a timezone issue.

### Disable a Site

Set interval to `None` or very large number:
```python
scraper_intervals = {
    "gcsurplus": 24,
    "gsa": None,        # Won't be scheduled
    "treasury": 48
}
```

---

## API Endpoints (Optional)

If you add the optional API endpoints from `SCHEDULER_API_ENDPOINTS.py`:

```bash
# Get status of all jobs
curl http://localhost:8001/api/scheduler/status

# Get status of specific site
curl http://localhost:8001/api/scheduler/jobs/gcsurplus

# Trigger immediate scrape
curl -X POST http://localhost:8001/api/scheduler/run/gsa

# Pause a site
curl -X POST http://localhost:8001/api/scheduler/pause/treasury

# Resume a site
curl -X POST http://localhost:8001/api/scheduler/resume/treasury

# Get next run time
curl http://localhost:8001/api/scheduler/next-run/gcsurplus
```

---

## Next Steps

1. **Read Full Configuration**: See `SCHEDULER_CONFIG.md` for advanced options
2. **Add API Endpoints**: Copy code from `SCHEDULER_API_ENDPOINTS.py` to `main.py` for runtime management
3. **Monitor Performance**: Check database load and adjust intervals as needed
4. **Set Up Alerts**: Log job failures and set up notifications
5. **Customize**: Adjust intervals and times for your use case

---

## Files to Review

- `config.py` - Configuration settings
- `scheduler.py` - Scheduler entry point
- `services/scheduler_service.py` - Core scheduler logic
- `SCHEDULER_CONFIG.md` - Comprehensive documentation
- `SCHEDULER_IMPLEMENTATION.md` - Implementation details
- `SCHEDULER_API_ENDPOINTS.py` - Optional management endpoints

---

## Still Have Questions?

1. Check `SCHEDULER_CONFIG.md` for detailed documentation
2. Review `services/scheduler_service.py` for source code comments
3. Check application logs for error messages
4. See [APScheduler Documentation](https://apscheduler.readthedocs.io/)
