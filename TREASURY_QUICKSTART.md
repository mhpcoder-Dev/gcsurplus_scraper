# Treasury.gov Scraper - Quick Start Guide

## 🚀 Getting Started

### 1. Test the Scraper

Test that the scraper works without affecting your database:

```bash
python test_treasury_scraper.py
```

This will:
- Fetch the Treasury.gov listing page
- Parse auction data
- Show sample properties
- Display statistics

Expected output:
```
✓ Successfully scraped XX items from Treasury.gov
✓ Scraper is working correctly and found XX auctions
```

### 2. Start the API Server

```bash
python start.py
```

Or:
```bash
uvicorn main:app --reload --port 8001
```

### 3. Trigger Treasury Scrape

**Option A: Via API**
```bash
curl -X POST http://localhost:8001/api/scrape/treasury
```

**Option B: Via Browser**
Visit: http://localhost:8001/docs

Then click on `POST /api/scrape/treasury` → Try it out → Execute

**Option C: Scrape All Sources**
```bash
curl -X POST http://localhost:8001/api/scrape/all
```

This will scrape GCSurplus, GSA, and Treasury.

### 4. View Results

**Get Treasury Auctions:**
```bash
curl http://localhost:8001/api/auctions/treasury
```

**Get All Upcoming Auctions:**
```bash
curl http://localhost:8001/api/auctions/upcoming
```

**View in Browser:**
- API Docs: http://localhost:8001/docs
- Root: http://localhost:8001/

## 📊 API Endpoints

### Treasury-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auctions/treasury` | GET | Get all Treasury real estate auctions |
| `/api/auctions/upcoming` | GET | Get all upcoming auctions (mainly Treasury) |
| `/api/scrape/treasury` | POST | Trigger Treasury scraper |

### Query Parameters

```bash
# Filter by location
curl "http://localhost:8001/api/auctions/treasury?search=California"

# Pagination
curl "http://localhost:8001/api/auctions/treasury?skip=0&limit=20"

# Combine filters
curl "http://localhost:8001/api/auctions/upcoming?source=treasury&asset_type=real-estate"
```

## 🗄️ Database Access

### Using Python

```python
from sqlalchemy.orm import Session
from core.database import get_db
from repositories.auction_repository import AuctionRepository

# Get database session
db = next(get_db())
repo = AuctionRepository(db)

# Get upcoming auctions
upcoming = repo.get_upcoming(limit=10)

# Get Treasury auctions specifically
treasury_items = repo.get_all(source='treasury', limit=50)

# Get statistics
stats = repo.get_stats()
print(f"Upcoming auctions: {stats['upcoming_auctions']}")
```

### SQL Query Examples

```sql
-- Get all Treasury auctions
SELECT * FROM auction_items WHERE source = 'treasury';

-- Get upcoming auctions with dates
SELECT title, location_city, location_state, closing_date, minimum_bid
FROM auction_items 
WHERE auction_type = 'upcoming'
ORDER BY closing_date ASC;

-- Count by state
SELECT location_state, COUNT(*) as count
FROM auction_items
WHERE source = 'treasury'
GROUP BY location_state
ORDER BY count DESC;
```

## 🔄 Automated Scraping

### Schedule Regular Scraping

Edit your scheduler or cron job:

```python
# In scheduler.py or your scheduling system
from apscheduler.schedulers.background import BackgroundScheduler

def scrape_treasury():
    # Your scraping logic
    service = AuctionService(db)
    service.scrape_source('treasury')

scheduler = BackgroundScheduler()
# Run weekly on Mondays at 9 AM
scheduler.add_job(scrape_treasury, 'cron', day_of_week='mon', hour=9)
scheduler.start()
```

### Using Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add weekly scrape (every Monday at 9 AM)
0 9 * * 1 cd /path/to/project && python -c "from services.auction_service import AuctionService; from core.database import get_db; db = next(get_db()); AuctionService(db).scrape_source('treasury')"
```

### Using Windows Task Scheduler

Create a batch file `scrape_treasury.bat`:
```batch
@echo off
cd E:\client\Brianne\MoneyMeta_Final\gcsurplus-scraper
python -c "from services.auction_service import AuctionService; from core.database import get_db; db = next(get_db()); AuctionService(db).scrape_source('treasury')"
```

Then schedule it in Task Scheduler.

## 📱 Frontend Integration

### Fetch Upcoming Auctions

```javascript
// In your Next.js/React component
const fetchUpcomingAuctions = async () => {
  const response = await fetch('http://localhost:8001/api/auctions/upcoming');
  const data = await response.json();
  return data.items;
};

// Or with filters
const fetchTreasuryAuctions = async (state) => {
  const response = await fetch(
    `http://localhost:8001/api/auctions/treasury?search=${state}`
  );
  const data = await response.json();
  return data.items;
};
```

### Display Upcoming Auctions Page

Create a new page: `app/upcoming/page.jsx`

```jsx
'use client';

import { useState, useEffect } from 'react';

export default function UpcomingAuctions() {
  const [auctions, setAuctions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8001/api/auctions/upcoming')
      .then(res => res.json())
      .then(data => {
        setAuctions(data.items);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Upcoming Real Estate Auctions</h1>
      {auctions.map(auction => (
        <div key={auction.lot_number}>
          <h2>{auction.title}</h2>
          <p>{auction.location_city}, {auction.location_state}</p>
          <p>Auction Date: {new Date(auction.closing_date).toLocaleDateString()}</p>
          <p>Starting Bid: ${auction.minimum_bid?.toLocaleString()}</p>
          {auction.extra_data?.deposit && (
            <p>Deposit Required: {auction.extra_data.deposit}</p>
          )}
          <a href={auction.item_url} target="_blank">View Details</a>
        </div>
      ))}
    </div>
  );
}
```

## 🐛 Troubleshooting

### Problem: No auctions found

**Solution:**
1. Check if there are active auctions on the website
2. Run the test script: `python test_treasury_scraper.py`
3. Check the website structure hasn't changed
4. Review logs for errors

### Problem: Detail pages not loading

**Solution:**
1. Detail pages may have temporary URLs
2. Check the `item_url` field in the database
3. Some auctions may not have detail pages yet
4. The scraper will still save listing page data

## 🐛 Troubleshooting

### Problem: No auctions found

**Solution:**
These are Pylance type checking warnings and won't prevent the code from running. The scraper handles these cases properly at runtime.

## 📈 Monitoring

### Check Scraper Status

```python
from services.auction_service import AuctionService
from core.database import get_db

db = next(get_db())
service = AuctionService(db)

# Get statistics
stats = service.get_statistics()
print(stats)

# Check Treasury auctions
treasury_count = service.repository.count(source='treasury')
print(f"Treasury auctions in database: {treasury_count}")
```

### View Logs

The scraper logs all activities. Check for:
- Number of items scraped
- Errors during scraping
- Detail page access success rate

## 🔧 Configuration

### Update Treasury URLs

If the Treasury website changes, update in `config.py`:

```python
treasury_base_url: str = "https://www.treasury.gov/auctions/treasury/rp"
treasury_listing_url: str = "https://www.treasury.gov/auctions/treasury/rp/realprop.shtml"
```

### Environment Variables

Create a `.env` file:

```env
# Database
database_url=postgresql://user:pass@host/db

# Treasury Settings
treasury_base_url=https://www.treasury.gov/auctions/treasury/rp
treasury_listing_url=https://www.treasury.gov/auctions/treasury/rp/realprop.shtml

# Scraping
request_timeout=30
max_retries=3
```

## 📝 Best Practices

1. **Test Before Production**: Use `test_treasury_scraper.py` to verify functionality
2. **Schedule Wisely**: Treasury auctions don't change frequently - weekly scraping is sufficient
3. **Monitor Logs**: Check logs regularly for errors or changes
4. **Handle Missing Data**: Some fields may be "Currently not available" - design UI accordingly
5. **Separate Upcoming/Active**: Filter by `status='upcoming'` vs `status='active'` in frontend

## 🆘 Getting Help

1. **Check README**: `README_TREASURY.md` for detailed documentation
2. **Run Tests**: `python test_treasury_scraper.py`
3. **Review Logs**: Check application logs for detailed error messages
4. **API Docs**: Visit http://localhost:8001/docs for interactive API documentation

## 🎯 Next Steps

1. ✅ Test scraper
2. ✅ Trigger first scrape
3. ✅ Verify data in database
4. ✅ Integrate with frontend
5. ✅ Set up automated scraping
6. ✅ Monitor and maintain
