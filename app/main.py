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
    init_db()


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
            "docs": "/docs"
        }
    }


@app.get("/api/auctions")
async def list_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return (max 500)"),
    status: Optional[str] = Query(None, description="Filter by status (active, closed, expired)"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    country: Optional[str] = Query(None, description="Filter by country (Canada, USA)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get list of auction items with pagination and filters.
    """
    # Cap the limit to prevent excessive queries
    limit = min(limit, 500)
    items = crud.get_all_items(db, skip=skip, limit=limit, status=status, search=search, country=country, category=category)
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


@app.post("/api/migrate")
async def migrate_database():
    """
    Run database migration to add country and category columns.
    Safe to run multiple times - will not affect existing data.
    """
    from sqlalchemy import text
    from app.database import engine
    
    migration_steps = []
    
    try:
        with engine.connect() as connection:
            # Step 1: Add country column with default value
            try:
                connection.execute(text("""
                    ALTER TABLE auction_items 
                    ADD COLUMN IF NOT EXISTS country VARCHAR(50) DEFAULT 'Canada'
                """))
                connection.commit()
                migration_steps.append("✓ Added 'country' column")
            except Exception as e:
                migration_steps.append(f"✓ Country column exists or error: {str(e)[:50]}")
            
            # Step 2: Create index on country
            try:
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auction_items_country 
                    ON auction_items(country)
                """))
                connection.commit()
                migration_steps.append("✓ Created index on 'country'")
            except Exception as e:
                migration_steps.append(f"✓ Country index exists")
            
            # Step 3: Add category column
            try:
                connection.execute(text("""
                    ALTER TABLE auction_items 
                    ADD COLUMN IF NOT EXISTS category VARCHAR(100)
                """))
                connection.commit()
                migration_steps.append("✓ Added 'category' column")
            except Exception as e:
                migration_steps.append(f"✓ Category column exists or error: {str(e)[:50]}")
            
            # Step 4: Create index on category
            try:
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_auction_items_category 
                    ON auction_items(category)
                """))
                connection.commit()
                migration_steps.append("✓ Created index on 'category'")
            except Exception as e:
                migration_steps.append(f"✓ Category index exists")
            
            # Step 5: Update existing records with country='Canada' if NULL
            try:
                result = connection.execute(text("""
                    UPDATE auction_items 
                    SET country = 'Canada' 
                    WHERE country IS NULL
                """))
                connection.commit()
                migration_steps.append(f"✓ Updated {result.rowcount} rows with default country")
            except Exception as e:
                migration_steps.append(f"✓ Country update: {str(e)[:50]}")
            
            # Step 6: Update existing records with categories based on titles
            try:
                from app.scraper import GCSurplusScraper
                
                result = connection.execute(text("""
                    SELECT id, title FROM auction_items WHERE category IS NULL
                """))
                rows = result.fetchall()
                
                updated = 0
                for row_id, title in rows:
                    category = GCSurplusScraper.extract_category(title)
                    connection.execute(
                        text("UPDATE auction_items SET category = :cat WHERE id = :id"),
                        {"cat": category, "id": row_id}
                    )
                    updated += 1
                
                connection.commit()
                migration_steps.append(f"✓ Auto-detected categories for {updated} existing items")
            except Exception as e:
                migration_steps.append(f"✓ Category detection: {str(e)[:100]}")
        
        return {
            "status": "success",
            "message": "Migration completed successfully",
            "steps": migration_steps
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Migration failed: {str(e)}",
            "steps": migration_steps
        }
