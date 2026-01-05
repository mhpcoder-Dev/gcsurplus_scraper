from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import logging

from core.database import get_db, init_db
from services import AuctionService
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Source Auction Scraper API",
    description="Unified API for scraping and accessing government auction data from multiple sources",
    version="3.0.0"
)

# Configure CORS for Next.js
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]

# Add production URLs from environment
if os.getenv("FRONTEND_URL"):
    allowed_origins.append(os.getenv("FRONTEND_URL"))
if os.getenv("NEXT_PUBLIC_URL"):
    allowed_origins.append(os.getenv("NEXT_PUBLIC_URL"))

# Add Vercel preview deployments
allowed_origins.append("https://*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting FastAPI application")
    logger.info(f"Database URL: {settings.database_url[:20]}...")
    init_db()
    logger.info("Database initialized successfully")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multi-Source Auction Scraper API",
        "version": "3.0.0",
        "sources": ["gcsurplus", "gsa", "treasury"],
        "endpoints": {
            "auctions": "/api/auctions (unified endpoint for all sources)",
            "upcoming": "/api/auctions/upcoming (future auctions like Treasury)",
            "gcsurplus": "/api/auctions/gcsurplus",
            "gsa": "/api/auctions/gsa",
            "treasury": "/api/auctions/treasury",
            "stats": "/api/stats",
            "scrape_all": "/api/scrape/all",
            "scrape_gcsurplus": "/api/scrape/gcsurplus",
            "scrape_gsa": "/api/scrape/gsa",
            "scrape_treasury": "/api/scrape/treasury",
            "docs": "/docs"
        }
    }


@app.get("/api/auctions")
async def get_all_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[List[str]] = Query(None, description="Filter by status (can specify multiple: active, scheduled, upcoming, closed, expired)"),
    source: Optional[str] = Query(None, description="Filter by source (gcsurplus, gsa, treasury, all)"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: Session = Depends(get_db)
):
    """
    Get unified list of auction items from all sources with pagination and filters.
    Supports multiple status values to fetch both 'scheduled' (GSA) and 'upcoming' (Treasury) auctions.
    """
    logger.info(f"GET /api/auctions - skip={skip}, limit={limit}, source={source}, status={status}")
    service = AuctionService(db)
    
    # Handle multiple status values
    status_filter = None
    if status and len(status) > 0:
        # If multiple status values, we'll need to handle this in the query
        if len(status) == 1:
            status_filter = status[0]
        else:
            # Multiple statuses - query each and combine, but be smart about pagination
            # Fetch slightly more than needed to account for sorting after combination
            fetch_limit = skip + limit + 20  # Buffer for sorting
            all_items = []
            
            for stat in status:
                result = service.get_auctions(
                    skip=0,
                    limit=fetch_limit,  # Fetch enough for this page
                    status=stat,
                    source=source if source != 'all' else None,
                    asset_type=asset_type,
                    search=search
                )
                all_items.extend(result['items'])
            
            # Sort combined results by closing_date
            all_items.sort(key=lambda x: x.get('auctionEndDate') or '9999-12-31')
            
            # Apply pagination to combined results
            paginated_items = all_items[skip:skip + limit]
            
            # For total count, we need to query each status count
            total_count = 0
            for stat in status:
                count_result = service.repository.count(
                    status=stat,
                    source=source if source != 'all' else None,
                    asset_type=asset_type
                )
                total_count += count_result
            
            return {
                "items": paginated_items,
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "filters": {
                    "status": status,
                    "source": source,
                    "asset_type": asset_type,
                    "search": search
                }
            }
    
    # Single or no status - use existing logic
    result = service.get_auctions(
        skip=skip,
        limit=limit,
        status=status_filter,
        source=source if source != 'all' else None,
        asset_type=asset_type,
        search=search
    )
    
    return result



@app.get("/api/auctions/gcsurplus")
async def list_gcsurplus_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get Canadian GCSurplus auction items"""
    return await get_all_auctions(skip, limit, status, "gcsurplus", None, None, db)


@app.get("/api/auctions/gsa")
async def list_gsa_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get US GSA auction items"""
    return await get_all_auctions(skip, limit, status, "gsa", None, None, db)


@app.get("/api/auctions/treasury")
async def list_treasury_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get US Treasury real estate auction items (upcoming auctions)"""
    return await get_all_auctions(skip, limit, status, "treasury", None, None, db)


@app.get("/api/auctions/upcoming")
async def list_upcoming_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    source: Optional[str] = Query(None, description="Filter by source"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    db: Session = Depends(get_db)
):
    """
    Get upcoming auction items (status='upcoming', mainly Treasury.gov auctions).
    These are future auctions that haven't started bidding yet.
    """
    logger.info(f"GET /api/auctions/upcoming - skip={skip}, limit={limit}, source={source}")
    service = AuctionService(db)
    
    items = service.repository.get_upcoming(
        skip=skip,
        limit=limit,
        source=source,
        asset_type=asset_type
    )
    
    # Get total count
    total = service.repository.count(status="upcoming", source=source, asset_type=asset_type)
    
    # Transform to API format
    items_dict = [service._transform_to_api_format(item) for item in items]
    
    return {
        "items": items_dict,
        "total": total,
        "skip": skip,
        "limit": limit,
        "filters": {
            "status": "upcoming",
            "source": source,
            "asset_type": asset_type
        }
    }


@app.get("/api/auctions/{lot_number}")
async def get_auction(
    lot_number: str,
    source: Optional[str] = Query(None, description="Source of the auction"),
    db: Session = Depends(get_db)
):
    """
    Get specific auction item by lot number.
    """
    service = AuctionService(db)
    item = service.get_auction_by_lot_number(lot_number, source)
    
    if not item:
        raise HTTPException(status_code=404, detail="Auction item not found")
    
    return item


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get database statistics.
    """
    service = AuctionService(db)
    return service.get_statistics()


@app.post("/api/scrape/all")
async def scrape_all_sources(background_tasks: BackgroundTasks):
    """
    Manually trigger scraping for ALL sources (GCSurplus + GSA + Treasury).
    """
    logger.info("POST /api/scrape/all - Manual scrape triggered")
    
    def run_all_scrapes():
        db_session = next(get_db())
        try:
            logger.info("Background task: Starting scrape for all sources")
            service = AuctionService(db_session)
            results = service.scrape_all_sources()
            logger.info(f"✓ All sources scraped successfully: {results}")
        except Exception as e:
            logger.error(f"✗ Error during scrape: {e}", exc_info=True)
        finally:
            db_session.close()
            logger.debug("Database session closed")
    
    background_tasks.add_task(run_all_scrapes)
    
    return {
        "message": "Scraping started for all sources (GCSurplus + GSA + Treasury)",
        "status": "processing"
    }


@app.post("/api/scrape/cron")
async def scrape_cron(authorization: str = Header(None), background_tasks: BackgroundTasks = BackgroundTasks()):
    """
    Cron endpoint for scheduled jobs (hourly updates).
    Scrapes all sources and updates database.
    """
    # Verify authorization
    cron_secret = os.getenv("CRON_SECRET")
    if cron_secret and authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    def run_all_scrapes():
        db_session = next(get_db())
        try:
            service = AuctionService(db_session)
            service.scrape_all_sources()
            print("Cron: All sources scraped successfully")
        except Exception as e:
            print(f"Cron error: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(run_all_scrapes)
    return {"message": "Cron scraping job started for all sources"}


@app.post("/api/scrape/gcsurplus")
async def scrape_gcsurplus(background_tasks: BackgroundTasks):
    """
    Manually trigger scraping for GCSurplus only.
    """
    def run_scrape():
        db_session = next(get_db())
        try:
            service = AuctionService(db_session)
            result = service.scrape_source("gcsurplus")
            print(f"GCSurplus: {result}")
        except Exception as e:
            print(f"Error during GCSurplus scraping: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(run_scrape)
    return {"message": "GCSurplus scraping job started"}


@app.post("/api/scrape/gsa")
async def scrape_gsa(background_tasks: BackgroundTasks):
    """
    Manually trigger scraping for GSA only.
    """
    def run_scrape():
        db_session = next(get_db())
        try:
            service = AuctionService(db_session)
            result = service.scrape_source("gsa")
            print(f"GSA: {result}")
        except Exception as e:
            print(f"Error during GSA scraping: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(run_scrape)
    return {"message": "GSA scraping job started"}


@app.post("/api/scrape/treasury")
async def scrape_treasury(background_tasks: BackgroundTasks):
    """
    Manually trigger scraping for Treasury.gov real estate auctions.
    """
    def run_scrape():
        db_session = next(get_db())
        try:
            service = AuctionService(db_session)
            result = service.scrape_source("treasury")
            print(f"Treasury: {result}")
        except Exception as e:
            print(f"Error during Treasury scraping: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(run_scrape)
    return {"message": "Treasury scraping job started"}


@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Get database statistics"""
    service = AuctionService(db)
    return service.get_statistics()


@app.delete("/api/cleanup")
async def cleanup_old_items(days: int = Query(30, description="Delete items older than X days"), db: Session = Depends(get_db)):
    """Delete old unavailable items"""
    service = AuctionService(db)
    deleted_count = service.repository.delete_old(days_old=days)
    return {"message": f"Deleted {deleted_count} old items", "days": days}