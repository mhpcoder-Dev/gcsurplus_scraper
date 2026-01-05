# Multi-Source Auction Scraper API

Unified FastAPI backend for scraping and serving government auction data from multiple sources.

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Next.js App   │────────>│   FastAPI API    │────────>│  PostgreSQL │
│   (Frontend)    │         │   (Backend)      │         │  Database   │
└─────────────────┘         └──────────────────┘         └─────────────┘
                                     │
                                     │  Scrapes Data
                                     ▼
                            ┌─────────────────┐
                            │ Auction Sources │
                            │ • GCSurplus.ca  │
                            │ • GSA Auctions  │
                            │ • (Future sites)│
                            └─────────────────┘
```

## Supported Auction Sources

1. **GCSurplus** (Canadian Government Surplus)
   - Source: `gcsurplus`
   - Scraper: `app/scrapers/gcsurplus.py`
   
2. **GSA Auctions** (US General Services Administration)
   - Source: `gsa`
   - Scraper: `app/scrapers/gsa.py`

## Project Structure

```
gcsurplus-scraper/
├── app/
│   ├── scrapers/           # Modular scraper system
│   │   ├── __init__.py
│   │   ├── base.py         # Base scraper class (interface)
│   │   ├── gcsurplus.py    # GCSurplus scraper
│   │   └── gsa.py          # GSA Auctions scraper
│   ├── main.py             # FastAPI app & unified endpoints
│   ├── database.py         # SQLAlchemy models (unified schema)
│   ├── crud.py             # Database operations
│   ├── config.py           # Configuration
│   └── scheduler.py        # APScheduler for hourly updates
├── requirements.txt
└── README_ARCHITECTURE.md  # This file
```

## Database Schema

**Single unified `auction_items` table** supports all sources:

```python
- lot_number (unique, indexed)    # Unique ID per source
- source (indexed)                # 'gcsurplus', 'gsa', etc.
- title, description
- current_bid, minimum_bid, bid_increment
- status (active/closed/expired)
- location_city, location_province, location_state
- closing_date, bid_date
- image_urls (JSON array)
- contact_name, contact_phone, contact_email
- agency, asset_type
- item_url
- extra_data (JSON)               # Source-specific fields
```

## API Endpoints

### Data Endpoints
- `GET /api/auctions` - Get all auctions (unified)
  - Query params: `source`, `status`, `asset_type`, `search`, `skip`, `limit`
- `GET /api/auctions/gcsurplus` - Canadian auctions only
- `GET /api/auctions/gsa` - US GSA auctions only
- `GET /api/auctions/{lot_number}` - Get specific auction
- `GET /api/stats` - Database statistics

### Scraping Endpoints
- `POST /api/scrape/all` - Manually trigger all sources
- `POST /api/scrape/gcsurplus` - Scrape GCSurplus only
- `POST /api/scrape/gsa` - Scrape GSA only
- `POST /api/scrape/cron` - Hourly automated scraping (with auth)

## Setup Instructions

### 1. Database Setup (PostgreSQL)

Use a free PostgreSQL provider:
- **Neon** (https://neon.tech) - Recommended, generous free tier
- **Supabase** (https://supabase.com)
- **Railway** (https://railway.app)

Get your connection string (format: `postgresql://user:password@host:port/database`)

### 2. Environment Variables

Create `.env` file in `gcsurplus-scraper/`:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# GSA API
GSA_API_KEY=rXyfDnTjMh3d0Zu56fNcMbHb5dgFBQrmzfTjZqq3
GSA_API_BASE_URL=https://api.gsa.gov/assets/gsaauctions/v2

# Security
CRON_SECRET=your-random-secret-string

# API Settings
API_PORT=8001
API_HOST=0.0.0.0

# Scraping
DELETE_CLOSED_IMMEDIATELY=true
```

### 3. Install Dependencies

```bash
cd gcsurplus-scraper
pip install -r requirements.txt
```

### 4. Run Locally

```bash
# Option 1: Using uvicorn directly
uvicorn app.main:app --reload --port 8001

# Option 2: Using Python
python -m app.main

# Option 3: With scheduler (hourly updates)
python run.py
```

### 5. Run Initial Scrape

```bash
# Test individual scrapers
curl -X POST http://localhost:8001/api/scrape/gcsurplus
curl -X POST http://localhost:8001/api/scrape/gsa

# Or scrape all sources at once
curl -X POST http://localhost:8001/api/scrape/all
```

### 6. Next.js Configuration

In your Next.js app, create `.env.local`:

```env
FASTAPI_URL=http://localhost:8001
# Or in production:
# FASTAPI_URL=https://your-fastapi-url.com
```

Update Next.js to use the new proxy routes (already done in `route_new.js` files).

## Deployment

### FastAPI Deployment Options

1. **Railway** (Easiest)
   - Connect GitHub repo
   - Auto-detects Python
   - Add environment variables
   - Deploy!

2. **Render**
   - Free tier available
   - Good for background workers
   
3. **Fly.io**
   - Free tier with good performance
   - Need to create `Dockerfile`

4. **DigitalOcean App Platform**
   - $5/month
   - Very reliable

### Scheduled Updates (Hourly)

**Option 1: Built-in APScheduler** (when using Railway/Render/Fly.io)
```python
# Already configured in scheduler.py
# Runs hourly automatically when server starts
```

**Option 2: External Cron Service** (if using serverless)
- Use **cron-job.org** or **EasyCron**
- Schedule POST request to `/api/scrape/cron`
- Add header: `Authorization: Bearer YOUR_CRON_SECRET`

**Option 3: Vercel Cron** (if deploying FastAPI to Vercel)
```json
{
  "crons": [{
    "path": "/api/scrape/cron",
    "schedule": "0 * * * *"
  }]
}
```

## Adding New Auction Sources

To add a new site (e.g., eBay Government Auctions):

1. **Create new scraper**: `app/scrapers/ebay.py`
```python
from app.scrapers.base import BaseScraper

class EbayScraper(BaseScraper):
    def get_source_name(self):
        return 'ebay'
    
    def scrape_all(self):
        # Implement scraping logic
        pass
    
    def scrape_single(self, item_id):
        # Implement single item fetch
        pass
```

2. **Register in `__init__.py`**:
```python
from app.scrapers.ebay import EbayScraper
__all__ = ['BaseScraper', 'GCSurplusScraper', 'GSAScraper', 'EbayScraper']
```

3. **Add endpoint in `main.py`**:
```python
@app.post("/api/scrape/ebay")
async def scrape_ebay(background_tasks: BackgroundTasks):
    # Add scraping logic
    pass
```

4. **Update `scrape_all_sources` function** to include new scraper

That's it! The unified database schema handles all sources automatically.

## Benefits of This Architecture

✅ **Centralized Data Storage** - All auction data in one database
✅ **Fast Response Times** - No real-time scraping, serve from DB
✅ **Reduced Server Load** - Next.js just proxies, doesn't scrape
✅ **Easy to Scale** - Add new sources without touching frontend
✅ **Hourly Updates** - Fresh data without user-facing delays
✅ **Modular Design** - Each scraper is independent
✅ **Type Safety** - Base scraper ensures consistent interface
✅ **Free Tier Friendly** - Optimized for free database limits

## Monitoring & Maintenance

- Check `/api/stats` for database health
- Monitor scraping logs in FastAPI console
- Set up alerts for failed scrapes (optional)
- Database auto-deletes closed auctions to save space

## Performance Tips

1. **Database Indexing** - Already indexed on: `lot_number`, `source`, `status`, `asset_type`, `closing_date`
2. **Next.js Caching** - API routes cache FastAPI responses for 5 minutes
3. **Pagination** - Always use `skip` and `limit` parameters
4. **Filtering** - Filter by `source` or `asset_type` for faster queries

## Support

For issues or questions:
1. Check FastAPI docs: http://localhost:8001/docs
2. Review logs in terminal
3. Test scrapers individually before combined scraping
