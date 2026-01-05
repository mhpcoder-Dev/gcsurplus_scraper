"""
Auction Service - Business Logic Layer
Handles business logic and orchestrates between repositories and scrapers.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json
import logging

from repositories.auction_repository import AuctionRepository
from scrapers import GCSurplusScraper, GSAScraper, TreasuryScraper
from config import settings

logger = logging.getLogger(__name__)


class AuctionService:
    """
    Service layer for auction business logic.
    Orchestrates operations between repositories and external services.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuctionRepository(db)
    
    def get_auctions(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        source: Optional[str] = None,
        asset_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict:
        """
        Get auctions with filters and transform to API format.
        Business logic: pagination, filtering, transformation.
        Optimized to run count and fetch in parallel.
        """
        import time
        start_time = time.time()
        
        # Fetch items and count separately (can be optimized with threads if needed)
        items = self.repository.get_all(
            skip=skip,
            limit=limit,
            status=status,
            source=source,
            asset_type=asset_type,
            search=search
        )
        
        # Only get count if not searching (count is expensive with search)
        # For search, we'll return the count of current page
        if search:
            total = len(items) + skip  # Approximate
            logger.info(f"Search query - returning approximate count: {total}")
        else:
            total = self.repository.count(
                status=status,
                source=source,
                asset_type=asset_type
            )
        
        # Transform to API format
        items_dict = [self._transform_to_api_format(item) for item in items]
        
        elapsed = time.time() - start_time
        logger.info(f"get_auctions completed in {elapsed:.3f}s - {len(items_dict)} items returned")
        
        return {
            "items": items_dict,
            "total": total,
            "skip": skip,
            "limit": limit,
            "filters": {
                "status": status,
                "source": source,
                "asset_type": asset_type,
                "search": search
            }
        }
    
    def get_auction_by_lot_number(
        self, 
        lot_number: str, 
        source: Optional[str] = None
    ) -> Optional[Dict]:
        """Get single auction by lot number"""
        item = self.repository.get_by_lot_number(lot_number, source)
        
        if not item:
            return None
        
        return self._transform_to_api_format(item)
    
    def create_or_update_auction(self, item_data: Dict) -> Dict:
        """
        Create or update auction item.
        Business logic: check if exists, create or update accordingly.
        """
        existing_item = self.repository.get_by_lot_number(
            item_data["lot_number"],
            item_data.get("source", "gcsurplus")
        )
        
        if existing_item:
            updated_item = self.repository.update(existing_item, item_data)
            logger.debug(f"Updated auction: {item_data['lot_number']}")
            return self._transform_to_api_format(updated_item)
        else:
            new_item = self.repository.create(item_data)
            logger.debug(f"Created auction: {item_data['lot_number']}")
            return self._transform_to_api_format(new_item)
    
    def scrape_source(self, source: str) -> Dict:
        """
        Scrape a specific auction source and update database.
        Business logic: orchestrates scraping and database updates.
        """
        logger.info(f"Starting scrape for source: {source}")
        
        # Get appropriate scraper
        if source == "gcsurplus":
            scraper = GCSurplusScraper()
        elif source == "gsa":
            scraper = GSAScraper()
        elif source == "treasury":
            scraper = TreasuryScraper()
        else:
            raise ValueError(f"Unknown source: {source}")
        
        # Scrape data
        items = scraper.scrape_all()
        logger.info(f"Scraped {len(items)} items from {source}")
        
        # Update database
        created_count = 0
        updated_count = 0
        
        for item_data in items:
            existing = self.repository.get_by_lot_number(
                item_data["lot_number"],
                source
            )
            
            if existing:
                self.repository.update(existing, item_data)
                updated_count += 1
            else:
                self.repository.create(item_data)
                created_count += 1
        
        # Mark items not in scrape as unavailable
        lot_numbers = [item["lot_number"] for item in items]
        marked_count = self.repository.mark_unavailable(lot_numbers, source)
        
        # Delete old closed items if configured
        deleted_count = 0
        if settings.delete_closed_immediately:
            deleted_count = self.repository.delete_old(days=0)
        
        logger.info(
            f"Scrape complete for {source}: "
            f"{created_count} created, {updated_count} updated, "
            f"{marked_count} marked unavailable, {deleted_count} deleted"
        )
        
        return {
            "source": source,
            "scraped": len(items),
            "created": created_count,
            "updated": updated_count,
            "marked_unavailable": marked_count,
            "deleted": deleted_count
        }
    
    def scrape_all_sources(self) -> Dict:
        """
        Scrape all configured auction sources.
        Business logic: orchestrates multiple source scraping.
        """
        logger.info("Starting scrape for all sources")
        
        results = {}
        sources = ["gcsurplus", "gsa", "treasury"]
        
        for source in sources:
            try:
                results[source] = self.scrape_source(source)
            except Exception as e:
                logger.error(f"Error scraping {source}: {e}")
                results[source] = {
                    "source": source,
                    "error": str(e),
                    "scraped": 0,
                    "created": 0,
                    "updated": 0
                }
        
        total_scraped = sum(r.get("scraped", 0) for r in results.values())
        logger.info(f"All sources scrape complete: {total_scraped} total items")
        
        return {
            "results": results,
            "total_scraped": total_scraped
        }
    
    def get_statistics(self) -> Dict:
        """Get auction statistics"""
        return self.repository.get_stats()
    
    def _transform_to_api_format(self, item) -> Dict:
        """
        Transform database model to API response format.
        Business logic: data transformation and JSON parsing.
        """
        return {
            "id": item.id,
            "lot_number": item.lot_number,
            "sale_number": item.sale_number,
            "source": item.source,
            "title": item.title,
            "description": item.description,
            "current_bid": item.current_bid,
            "minimum_bid": item.minimum_bid,
            "bid_increment": item.bid_increment,
            "next_minimum_bid": item.next_minimum_bid,
            "quantity": item.quantity,
            "status": item.status,
            "is_available": item.is_available,
            "location_city": item.location_city,
            "location_province": item.location_province,
            "location_state": item.location_state,
            "location_address": item.location_address,
            "closing_date": item.closing_date.isoformat() if item.closing_date else None,
            "bid_date": item.bid_date.isoformat() if item.bid_date else None,
            "time_remaining": item.time_remaining,
            "image_urls": json.loads(item.image_urls) if item.image_urls else [],
            "contact_name": item.contact_name,
            "contact_phone": item.contact_phone,
            "contact_email": item.contact_email,
            "agency": item.agency,
            "asset_type": item.asset_type,
            "item_url": item.item_url,
            "extra_data": json.loads(item.extra_data) if item.extra_data else {},
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        }
