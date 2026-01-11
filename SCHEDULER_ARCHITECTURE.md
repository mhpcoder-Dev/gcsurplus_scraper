# Scheduler Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│                         (main.py)                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Startup Event
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Scheduler Initialization                       │
│                      (scheduler.py)                             │
│                                                                 │
│  • start_scheduler()                                            │
│  • Loads configuration from config.py                           │
│  • Creates SchedulerService instance                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Initializes
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SchedulerService                             │
│              (services/scheduler_service.py)                    │
│                                                                 │
│  • APScheduler (AsyncIOScheduler)                               │
│  • Per-site job configuration                                   │
│  • Event listeners (success/error tracking)                     │
│  • Job management (pause/resume/trigger)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Creates Jobs
                         ↓
            ┌────────────┴────────────┐
            │                         │
┌───────────▼─────────┐   ┌──────────▼──────────┐   ┌──────────▼──────────┐
│   Job: GCSurplus    │   │    Job: GSA         │   │  Job: Treasury      │
│                     │   │                     │   │                     │
│  Schedule: 24h      │   │  Schedule: 12h      │   │  Schedule: 48h      │
│  or "02:00"         │   │  or "01:00,13:00"   │   │  or "03:00"         │
└──────────┬──────────┘   └──────────┬──────────┘   └──────────┬──────────┘
           │                         │                         │
           │ On Schedule             │ On Schedule             │ On Schedule
           ↓                         ↓                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              _run_scraper_job(site_name, scraper_class)         │
│                                                                 │
│  1. Initialize scraper (GCSurplusScraper/GSAScraper/etc)        │
│  2. scraper.scrape_all() → Returns list of items               │
│  3. Create AuctionService(db)                                   │
│  4. service.save_scraped_items(items) → Saves to database      │
│  5. Log results and update job status                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Saves to
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   AuctionService                                │
│              (services/auction_service.py)                      │
│                                                                 │
│  save_scraped_items(items):                                     │
│    • For each item:                                             │
│      - Check if exists (by lot_number + source)                 │
│      - Update if exists                                         │
│      - Create if new                                            │
│    • Return count of saved items                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Uses
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  AuctionRepository                              │
│             (repositories/auction_repository.py)                │
│                                                                 │
│  • get_by_lot_number(lot_number, source)                        │
│  • create(item_data)                                            │
│  • update(existing, item_data)                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Persists to
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Database                                   │
│                  (SQLite / PostgreSQL)                          │
│                                                                 │
│  Table: auction_items                                           │
│    • lot_number (unique per source)                             │
│    • source (gcsurplus/gsa/treasury)                            │
│    • title, description, price, etc.                            │
│    • updated_at, created_at                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       config.py                                 │
│                                                                 │
│  scraper_intervals = {                                          │
│    "gcsurplus": 24,  ──────┐                                    │
│    "gsa": 12,        ──────┤                                    │
│    "treasury": 48    ──────┤                                    │
│  }                         │                                    │
│                            │                                    │
│  scraper_schedule_times = {│                                    │
│    "gcsurplus": "02:00",   │                                    │
│    "gsa": "01:00,13:00",   │                                    │
│  }                         │                                    │
│                            │                                    │
│  scheduler_timezone = "UTC"│                                    │
│  scheduler_enabled = True  │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             │ Configuration loaded by
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SchedulerService                             │
│                                                                 │
│  add_site_job(site_name, interval, schedule_times):             │
│    • Check schedule_times first (priority)                      │
│    • Fall back to interval if no schedule_times                 │
│    • Create CronTrigger or IntervalTrigger                      │
│    • Add job to APScheduler                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Execution Timeline Example

```
Time    │ GCSurplus (24h)  │ GSA (12h)        │ Treasury (48h)
────────┼──────────────────┼──────────────────┼─────────────────
00:00   │                  │                  │
02:00   │ ▶ SCRAPE ✓       │                  │
04:00   │                  │                  │
06:00   │                  │ ▶ SCRAPE ✓       │
08:00   │                  │                  │
10:00   │                  │                  │
12:00   │                  │                  │
14:00   │                  │ ▶ SCRAPE ✓       │
16:00   │                  │                  │
18:00   │                  │                  │
20:00   │                  │                  │
22:00   │                  │                  │
──────  Day 2  ─────────────────────────────────────────────────
00:00   │                  │                  │
02:00   │ ▶ SCRAPE ✓       │ ▶ SCRAPE ✓       │ ▶ SCRAPE ✓
04:00   │                  │                  │
...     │ (repeats)        │ (repeats)        │ (repeats)
```

## Job State Machine

```
                       ┌─────────────────┐
                       │   SCHEDULED     │
                       │ (waiting for    │
                       │  next run time) │
                       └────────┬────────┘
                                │
                    Schedule    │
                    Time        │
                    Reached     │
                                ↓
                       ┌─────────────────┐
                       │    SUBMITTED    │
                       │ (job queued)    │
                       └────────┬────────┘
                                │
                                ↓
                       ┌─────────────────┐
                       │    RUNNING      │
                       │ (executing)     │
                       └────────┬────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ↓                       ↓
           ┌─────────────────┐    ┌─────────────────┐
           │    SUCCESS      │    │     ERROR       │
           │ (completed)     │    │  (exception)    │
           └────────┬────────┘    └────────┬────────┘
                    │                       │
                    │                       │
                    └───────────┬───────────┘
                                │
                    Re-schedule │
                                ↓
                       ┌─────────────────┐
                       │   SCHEDULED     │
                       │ (next run time) │
                       └─────────────────┘
```

## Event Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    Event: Job Submitted                        │
│  _job_submitted_listener()                                     │
│  • Log: "Job {id} submitted"                                   │
└────────────────────────────────────────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────────┐
│                   Event: Job Executing                         │
│  _run_scraper_job()                                            │
│  • Initialize scraper                                          │
│  • Scrape items                                                │
│  • Save to database                                            │
└────────────────────────────────────────────────────────────────┘
                               ↓
                    ┌──────────┴──────────┐
                    │                     │
                    ↓                     ↓
┌──────────────────────────────┐  ┌──────────────────────────────┐
│  Event: Job Executed         │  │  Event: Job Error            │
│  _job_executed_listener()    │  │  _job_error_listener()       │
│  • Log success               │  │  • Log error + stack trace   │
│  • Update job_status[id]     │  │  • Update job_status[id]     │
│    - status = 'success'      │  │    - status = 'error'        │
│    - last_run = now()        │  │    - error = exception       │
└──────────────────────────────┘  └──────────────────────────────┘
```

## Directory Structure

```
gcsurplus-scraper/
│
├── scheduler.py ─────────────────┐ Entry point
│                                 │ • start_scheduler()
│                                 │ • stop_scheduler()
│                                 │ • get_scheduler()
│
├── config.py ────────────────────┐ Configuration
│                                 │ • scraper_intervals
│                                 │ • scraper_schedule_times
│                                 │ • scheduler_timezone
│
├── main.py ──────────────────────┐ FastAPI integration
│                                 │ • startup: start_scheduler()
│                                 │ • shutdown: stop_scheduler()
│
├── services/
│   ├── scheduler_service.py ────┐ Core scheduler logic
│   │                             │ • SchedulerService class
│   │                             │ • Job management
│   │                             │ • Event handling
│   │
│   └── auction_service.py ───────┐ Business logic
│                                 │ • save_scraped_items()
│                                 │ • scrape_source()
│
├── scrapers/
│   ├── base.py ──────────────────┐ Base scraper interface
│   ├── gcsurplus.py ──────────────┐ GCSurplus scraper
│   ├── gsa.py ────────────────────┐ GSA scraper
│   └── treasury.py ───────────────┐ Treasury scraper
│
└── Documentation/
    ├── README_SCHEDULER.md ──────┐ Main summary (this file)
    ├── SCHEDULER_QUICKSTART.md ──┐ 5-minute setup guide
    ├── SCHEDULER_CONFIG.md ───────┐ Configuration reference
    ├── SCHEDULER_IMPLEMENTATION.md─┐ Technical details
    └── SCHEDULER_API_ENDPOINTS.py ─┐ Optional HTTP endpoints
```

## Data Flow Example: Single Scrape Job

```
1. Trigger
   └─> APScheduler timer reaches scheduled time

2. Job Execution
   └─> SchedulerService._run_scraper_job("gcsurplus", GCSurplusScraper)
       │
       ├─> Initialize: scraper = GCSurplusScraper()
       │
       ├─> Scrape: items = scraper.scrape_all()
       │   └─> Returns: [
       │         {"lot_number": "123", "title": "Car", "price": 5000, ...},
       │         {"lot_number": "124", "title": "Truck", "price": 8000, ...},
       │       ]
       │
       ├─> Service: service = AuctionService(db)
       │
       └─> Save: service.save_scraped_items(items)
           │
           └─> For each item:
               ├─> Check: existing = repository.get_by_lot_number("123", "gcsurplus")
               │
               ├─> If exists:
               │   └─> Update: repository.update(existing, item_data)
               │       └─> SQL: UPDATE auction_items SET ... WHERE id = ...
               │
               └─> If new:
                   └─> Create: repository.create(item_data)
                       └─> SQL: INSERT INTO auction_items VALUES (...)

3. Result Logging
   └─> "Saved 2 items (0 created, 2 updated)"

4. Re-schedule
   └─> APScheduler automatically schedules next run (24 hours later)
```
