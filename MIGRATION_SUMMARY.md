# 🔄 Migration Summary: SQLite → PostgreSQL + Vercel

## Changes Made for Cloud Deployment

### 1. Database Migration
**From**: SQLite (local file database)
**To**: PostgreSQL (cloud-hosted)

**Files Modified**:
- `app/database.py`: Updated engine configuration for PostgreSQL
  - Removed SQLite-specific `check_same_thread` parameter
  - Added `pool_pre_ping` and `pool_recycle` for cloud connections
  - Changed string columns to have explicit lengths for PostgreSQL

- `app/config.py`: Database URL now uses environment variable
  - Default changed from `sqlite:///./gcsurplus.db` to PostgreSQL format
  - Added `delete_closed_immediately` flag for free tier optimization

### 2. Dependencies Update
**File**: `requirements.txt`

**Removed**:
- `aiosqlite` - SQLite async driver (not needed)
- `apscheduler` - Not compatible with Vercel serverless

**Added**:
- `psycopg2-binary` - PostgreSQL driver

### 3. Serverless Architecture
**New Files Created**:
- `vercel.json` - Vercel configuration with cron jobs
- `api/index.py` - Serverless entry point for Vercel

**Scheduler Changes**:
- Removed `app/scheduler.py` dependency from `main.py`
- Replaced APScheduler with Vercel Cron Jobs
- Added new endpoint `/api/scrape/cron` for scheduled scraping

### 4. Free Tier Optimization
**File**: `app/crud.py`

**Changes**:
- `delete_old_items()` now defaults to 0 days (immediate deletion)
- Deletes both "closed" and "expired" statuses
- Automatically runs after each scrape to minimize database size

### 5. CORS Configuration
**File**: `app/main.py`

**Changes**:
- Updated CORS to allow `*.vercel.app` domains
- Added regex pattern matching for Vercel preview deployments
- Reads `NEXT_PUBLIC_URL` from environment for MoneyMeta integration

### 6. API Enhancements
**New Endpoint**: `POST /api/scrape/cron`
- Protected by `CRON_SECRET` authorization header
- Designed for Vercel Cron Jobs
- Includes automatic cleanup after scraping

### 7. Documentation
**New/Updated Files**:
- `README.md` - Complete rewrite with deployment instructions
- `DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment guide
- `.env.example` - Updated with PostgreSQL configuration

## Environment Variables Required

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ Yes |
| `CRON_SECRET` | Security token for cron endpoint | ⚠️ Recommended |
| `NEXT_PUBLIC_URL` | MoneyMeta app URL for CORS | ⚠️ If using MoneyMeta |

## Free Database Options

| Service | Free Tier | Pros | Cons |
|---------|-----------|------|------|
| **Neon** | 500MB | Serverless, fast, easy | Pauses after inactivity |
| **Supabase** | 500MB | Built-in APIs, no pause | More complex setup |
| **Railway** | 5GB (limited time) | More storage | Limited free tier |

## What Stays the Same

- ✅ Scraping logic (`app/scraper.py`)
- ✅ API endpoints structure
- ✅ Data models and schemas
- ✅ Auction item fields
- ✅ Search and filter functionality

## Migration Path (If Already Deployed Locally)

If you have existing SQLite data:

1. **Export Data** (optional):
   ```bash
   python -c "from app.database import *; import json; db = next(get_db()); items = db.query(AuctionItem).all(); print(json.dumps([{c.name: getattr(item, c.name) for c in item.__table__.columns} for item in items]))" > backup.json
   ```

2. **Deploy to Vercel**: Follow DEPLOYMENT_CHECKLIST.md

3. **Import Data** (optional):
   ```bash
   # Call /api/scrape/manual to fetch fresh data
   curl -X POST https://your-api.vercel.app/api/scrape/manual
   ```

## Deployment Workflow

```
┌─────────────────┐
│  Push Code      │
│  to GitHub      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Connect to     │
│  Vercel         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Add Database   │
│  (Neon/Supabase)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Add Env Vars   │
│  in Vercel      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Deploy         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Configure      │
│  Cron Jobs      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ✅ Live!       │
└─────────────────┘
```

## Cost Breakdown (Free Tier)

| Component | Cost | Notes |
|-----------|------|-------|
| Vercel Hosting | **$0** | Serverless functions, 100GB bandwidth |
| PostgreSQL (Neon) | **$0** | 500MB storage, unlimited queries |
| Domain | **$0** | Uses `*.vercel.app` subdomain |
| **Total** | **$0** | Perfect for side projects |

## Scaling Considerations

When you outgrow free tier:

1. **Database** (~$20/mo):
   - Neon Pro: 10GB storage
   - Supabase Pro: 8GB storage + 100GB bandwidth

2. **Vercel** (~$20/mo):
   - Pro plan: More function execution time
   - Better analytics

3. **Optimizations**:
   - Add caching layer (Redis)
   - Implement webhook instead of cron
   - Add CDN for images

## Testing Checklist

Before going live:

- [ ] Test database connection locally with cloud PostgreSQL
- [ ] Verify scraper works with current GCSurplus HTML
- [ ] Test all API endpoints return correct data
- [ ] Verify CORS works with MoneyMeta
- [ ] Check cron job executes successfully
- [ ] Confirm cleanup deletes old items
- [ ] Monitor database size stays under 500MB

## Rollback Plan

If deployment fails:

1. **Keep local version running**: Original SQLite version still works
2. **Vercel rollback**: Use Vercel dashboard to redeploy previous version
3. **Database**: Neon/Supabase have point-in-time recovery
4. **Code**: Git history preserves all changes

## Support Resources

- **Vercel Docs**: https://vercel.com/docs
- **Neon Docs**: https://neon.tech/docs
- **Supabase Docs**: https://supabase.com/docs
- **FastAPI on Vercel**: https://vercel.com/guides/python

---

**Migration Status**: ✅ Complete
**Ready for Deployment**: ✅ Yes
**Next Step**: Follow [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
