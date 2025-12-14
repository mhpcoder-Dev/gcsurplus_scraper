from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os

from app.database import get_db, init_db
from app.config import settings
from app import crud
from app.scraper import GCSurplusScraper

app = FastAPI(
    title="GCSurplus Scraper API",
    description="API for scraping and accessing GCSurplus.ca auction data",
    version="2.0.0"
)

# Configure CORS for Next.js
allowed_origins = [
    "http://localhost:3000",
    "https://*.vercel.app",
]

# Add environment-specific origins
if os.getenv("NEXT_PUBLIC_URL"):
    allowed_origins.append(os.getenv("NEXT_PUBLIC_URL"))

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
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GCSurplus Scraper API",
        "version": "2.0.0",
        "endpoints": {
            "auctions": "/api/auctions",
            "stats": "/api/stats",
            "scrape": "/api/scrape/manual",
            "init": "/api/init",
            "docs": "/docs"
        }
    }


@app.post("/api/init")
async def initialize_database():
    """Initialize database tables manually."""
    try:
        init_db()
        return {"message": "Database initialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")


@app.get("/api/auctions")
async def list_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(50, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status (active, closed, expired)"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: Session = Depends(get_db)
):
    """
    Get list of auction items with pagination and filters.
    """
    items = crud.get_all_items(db, skip=skip, limit=limit, status=status, search=search)
    return items


@app.get("/api/auctions/{lot_number}")
async def get_auction(lot_number: str, db: Session = Depends(get_db)):
    """
    Get specific auction item by lot number.
    """
    item = crud.get_item_by_lot_number(db, lot_number)
    if not item:
        raise HTTPException(status_code=404, detail="Auction item not found")
    return item


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get database statistics.
    """
    stats = crud.get_stats(db)
    return stats


@app.post("/api/scrape/manual")
async def scrape_now(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Manually trigger a scraping job.
    """
    def run_scrape():
        scraper = GCSurplusScraper()
        try:
            items = scraper.scrape_all()
            db_session = next(get_db())
            
            for item_data in items:
                crud.create_or_update_item(db_session, item_data)
            
            # Mark items as unavailable if they're no longer in the listing
            all_lot_numbers = [item["lot_number"] for item in items]
            crud.mark_items_as_unavailable(db_session, all_lot_numbers)
            
            # Immediately delete closed/removed items to save space
            if settings.delete_closed_immediately:
                deleted = crud.delete_old_items(db_session, days=0)
                print(f"Deleted {deleted} closed/removed items")
            
            db_session.close()
        except Exception as e:
            print(f"Error during scraping: {e}")
    
    background_tasks.add_task(run_scrape)
    return {"message": "Scraping job started in background"}


@app.post("/api/scrape/cron")
async def scrape_cron(
    authorization: Optional[str] = Header(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Cron endpoint for Vercel Cron Jobs.
    Vercel automatically includes the authorization header.
    """
    # Verify authorization from Vercel Cron
    cron_secret = os.getenv("CRON_SECRET")
    if cron_secret and authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    def run_scrape():
        scraper = GCSurplusScraper()
        try:
            items = scraper.scrape_all()
            db_session = next(get_db())
            
            for item_data in items:
                crud.create_or_update_item(db_session, item_data)
            
            all_lot_numbers = [item["lot_number"] for item in items]
            crud.mark_items_as_unavailable(db_session, all_lot_numbers)
            
            # Delete closed items immediately for free tier
            if settings.delete_closed_immediately:
                deleted = crud.delete_old_items(db_session, days=0)
                print(f"Deleted {deleted} closed/removed items")
            
            db_session.close()
        except Exception as e:
            print(f"Error during scraping: {e}")
    
    background_tasks.add_task(run_scrape)
    return {"message": "Cron scraping job started"}


@app.delete("/api/cleanup")
async def cleanup_old_items(db: Session = Depends(get_db)):
    """
    Delete old unavailable items.
    """
    deleted_count = crud.delete_old_items(db, days=0)
    return {"message": f"Deleted {deleted_count} old items"}
