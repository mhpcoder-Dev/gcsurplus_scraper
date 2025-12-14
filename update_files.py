"""
Script to update existing files for Vercel and PostgreSQL compatibility
"""
import os

# Update main.py to remove scheduler and add cron endpoint
main_py_content = '''from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query, Header
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
'''

# Update crud.py to delete closed items immediately
crud_py_update = '''from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import AuctionItem
from datetime import datetime, timedelta
from typing import List, Optional, Dict


def create_or_update_item(db: Session, item_data: Dict) -> AuctionItem:
    """
    Create a new auction item or update existing one.
    """
    existing_item = db.query(AuctionItem).filter(
        AuctionItem.lot_number == item_data["lot_number"]
    ).first()
    
    if existing_item:
        for key, value in item_data.items():
            setattr(existing_item, key, value)
        existing_item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        new_item = AuctionItem(**item_data)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item


def get_all_items(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[AuctionItem]:
    """
    Get all auction items with optional filters.
    """
    query = db.query(AuctionItem)
    
    if status:
        query = query.filter(AuctionItem.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                AuctionItem.title.ilike(search_term),
                AuctionItem.description.ilike(search_term)
            )
        )
    
    return query.offset(skip).limit(limit).all()


def get_item_by_lot_number(db: Session, lot_number: str) -> Optional[AuctionItem]:
    """
    Get auction item by lot number.
    """
    return db.query(AuctionItem).filter(AuctionItem.lot_number == lot_number).first()


def mark_items_as_unavailable(db: Session, current_lot_numbers: List[str]) -> int:
    """
    Mark items as closed if they're not in the current listing.
    """
    updated_count = db.query(AuctionItem).filter(
        AuctionItem.lot_number.notin_(current_lot_numbers),
        AuctionItem.status == "active"
    ).update({"status": "closed", "is_available": False}, synchronize_session=False)
    
    db.commit()
    return updated_count


def delete_old_items(db: Session, days: int = 0) -> int:
    """
    Delete closed/removed auction items immediately (days=0) to save database space.
    For free tier databases, we keep only active auctions.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Delete both closed and expired items immediately
    deleted_count = db.query(AuctionItem).filter(
        AuctionItem.status.in_(["closed", "expired"]),
        AuctionItem.updated_at < cutoff_date
    ).delete(synchronize_session=False)
    
    db.commit()
    return deleted_count


def get_stats(db: Session) -> Dict:
    """
    Get database statistics.
    """
    total = db.query(AuctionItem).count()
    active = db.query(AuctionItem).filter(AuctionItem.status == "active").count()
    closed = db.query(AuctionItem).filter(AuctionItem.status == "closed").count()
    expired = db.query(AuctionItem).filter(AuctionItem.status == "expired").count()
    
    return {
        "total_items": total,
        "active_auctions": active,
        "closed_auctions": closed,
        "expired_auctions": expired
    }
'''

# Write the files
print("Updating main.py...")
with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(main_py_content)

print("Updating crud.py...")
with open("app/crud.py", "w", encoding="utf-8") as f:
    f.write(crud_py_update)

print("\n✅ Files updated successfully!")
print("\nNext steps:")
print("1. Update .env with your PostgreSQL connection string")
print("2. Deploy to Vercel: vercel --prod")
print("3. Add DATABASE_URL in Vercel project settings")
print("4. Set up Vercel Cron Jobs in your Vercel dashboard")
