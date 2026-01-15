from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import logging

from core.database import get_db, init_db
from services import AuctionService
from services.comment_service import CommentService
from config import settings
from scheduler import start_scheduler, stop_scheduler
from schemas.comment import CommentCreate, CommentResponse, CommentListResponse
from schemas.auction import AuctionListResponse, AuctionDetailResponse

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

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]

# Add production URLs from settings
if settings.frontend_url:
    allowed_origins.append(settings.frontend_url)

# Add environment variable URLs (backward compatibility)
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
    """Initialize database and start scheduler on startup."""
    logger.info(f"Starting FastAPI application - Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Database URL: {settings.database_url[:30]}...")
    init_db()
    logger.info("Database initialized successfully")
    
    # Start the scheduler if enabled
    if settings.scheduler_enabled:
        scheduler = start_scheduler()
        if scheduler:
            logger.info("Background scheduler started successfully")
    else:
        logger.info("Scheduler disabled in settings")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown."""
    logger.info("Shutting down FastAPI application")
    stop_scheduler()
    logger.info("Scheduler stopped")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multi-Source Auction Scraper API",
        "version": "3.0.0",
        "sources": ["gcsurplus", "gsa", "treasury", "state_dept"],
        "endpoints": {
            "auctions": "/api/auctions (unified endpoint for all sources)",
            "upcoming": "/api/auctions/upcoming (future auctions like Treasury or State Dept Preparing)",
            "gcsurplus": "/api/auctions/gcsurplus",
            "gsa": "/api/auctions/gsa",
            "treasury": "/api/auctions/treasury",
            "state_dept": "/api/auctions/state_dept",
            "stats": "/api/stats",
            "comments": {
                "get": "GET /api/comments/{auction_id}",
                "create": "POST /api/comments",
                "delete": "DELETE /api/comments/{comment_id}",
                "count": "GET /api/comments/{auction_id}/count"
            },
            "scrape_all": "/api/scrape/all",
            "scrape_gcsurplus": "/api/scrape/gcsurplus",
            "scrape_gsa": "/api/scrape/gsa",
            "scrape_treasury": "/api/scrape/treasury",
            "scrape_state_dept": "/api/scrape/state_dept",
            "docs": "/docs"
        }
    }


@app.get("/api/auctions", response_model=AuctionListResponse)
async def get_all_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status (active, scheduled, upcoming, closed, expired)"),
    source: Optional[str] = Query(None, description="Filter by source (gcsurplus, gsa, treasury, all)"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: Session = Depends(get_db)
):
    """
    Get unified list of auction items from all sources with pagination and filters.
    Returns structured DTO response with only required fields.
    """
    logger.info(f"GET /api/auctions - skip={skip}, limit={limit}, source={source}, status={status}")
    service = AuctionService(db)
    
    # Get auctions using service (returns DTO)
    result = service.get_auctions(
        skip=skip,
        limit=limit,
        status=status,
        source=source if source != 'all' else None,
        asset_type=asset_type,
        search=search
    )
    
    return result



@app.get("/api/auctions/gcsurplus", response_model=AuctionListResponse)
async def list_gcsurplus_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get Canadian GCSurplus auction items"""
    return await get_all_auctions(skip, limit, status, "gcsurplus", None, None, db)


@app.get("/api/auctions/gsa", response_model=AuctionListResponse)
async def list_gsa_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get US GSA auction items"""
    return await get_all_auctions(skip, limit, status, "gsa", None, None, db)


@app.get("/api/auctions/treasury", response_model=AuctionListResponse)
async def list_treasury_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get US Treasury real estate auction items (upcoming auctions)"""
    return await get_all_auctions(skip, limit, status, "treasury", None, None, db)

@app.get("/api/auctions/state_dept", response_model=AuctionListResponse)
async def list_state_dept_auctions(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get US State Department auction items"""
    return await get_all_auctions(skip, limit, status, "state_dept", None, None, db)

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


@app.get("/api/auctions/{lot_number}", response_model=AuctionDetailResponse)
async def get_auction(
    lot_number: str,
    source: Optional[str] = Query(None, description="Source of the auction"),
    db: Session = Depends(get_db)
):
    """
    Get specific auction item by lot number.
    Returns detailed DTO response.
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


@app.post("/api/scrape/state_dept")
async def scrape_state_dept(background_tasks: BackgroundTasks):
    """
    Manually trigger scraping for State Department online auctions.
    """
    def run_scrape():
        db_session = next(get_db())
        try:
            service = AuctionService(db_session)
            result = service.scrape_source("state_dept")
            print(f"State Dept: {result}")
        except Exception as e:
            print(f"Error during State Dept scraping: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(run_scrape)
    return {"message": "State Department scraping job started"}


# ============================================================
# Comment Endpoints
# ============================================================

@app.get("/api/comments/{auction_id}")
async def get_comments(
    auction_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all comments for a specific auction.
    Returns comments sorted by newest first.
    """
    try:
        service = CommentService(db)
        comments = service.get_comments(auction_id)
        return {"comments": comments}
    except Exception as e:
        logger.error(f"Error fetching comments for auction {auction_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comments")


@app.post("/api/comments")
async def create_comment(
    comment_data: CommentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new comment on an auction.
    
    Request body:
    - auctionId: The auction lot number (required)
    - text: Comment text, 1-1000 characters (required)
    - author: Author name, max 100 characters (optional, defaults to "Anonymous")
    """
    try:
        service = CommentService(db)
        new_comment = service.create_comment(
            auction_id=comment_data.auctionId,
            text=comment_data.text,
            author=comment_data.author
        )
        return {"comment": new_comment}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@app.delete("/api/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a comment by ID.
    Returns 404 if comment not found.
    """
    try:
        service = CommentService(db)
        success = service.delete_comment(comment_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        return {"success": True, "message": "Comment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete comment")


@app.get("/api/comments/{auction_id}/count")
async def get_comment_count(
    auction_id: str,
    db: Session = Depends(get_db)
):
    """Get the number of comments for an auction"""
    try:
        service = CommentService(db)
        count = service.get_comment_count(auction_id)
        return {"auction_id": auction_id, "count": count}
    except Exception as e:
        logger.error(f"Error counting comments for auction {auction_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to count comments")
        db_session = next(get_db())
        try:
            service = AuctionService(db_session)
            result = service.scrape_source("state_dept")
            print(f"State Dept: {result}")
        except Exception as e:
            print(f"Error during State Dept scraping: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(run_scrape)
    return {"message": "State Department scraping job started"}


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