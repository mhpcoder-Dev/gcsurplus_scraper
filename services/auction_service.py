"""
Auction Service - Business Logic Layer
Handles business logic and orchestrates between repositories and scrapers.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json
import logging

from repositories.auction_repository import AuctionRepository
from scrapers import GCSurplusScraper, GSAScraper, TreasuryScraper, StateDeptScraper
from config import settings
from schemas.auction import (
    AuctionBase,
    AuctionDetailResponse,
    AuctionListResponse,
    AuctionLocation,
    AuctionBidding,
    AuctionContact,
    PaginationMeta
)

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
    ) -> AuctionListResponse:
        """
        Get auctions with filters and return DTO response.
        Business logic: pagination, filtering, transformation.
        Optimized to run count and fetch in parallel.
        """
        import time
        start_time = time.time()
        
        # Fetch items and count separately
        items = self.repository.get_all(
            skip=skip,
            limit=limit,
            status=status,
            source=source,
            asset_type=asset_type,
            search=search
        )
        
        # Only get count if not searching (count is expensive with search)
        if search:
            total = len(items) + skip  # Approximate
            logger.info(f"Search query - returning approximate count: {total}")
        else:
            total = self.repository.count(
                status=status,
                source=source,
                asset_type=asset_type
            )
        
        # Convert to DTOs
        items_dto = [self._model_to_base_dto(item) for item in items]
        
        # Calculate pagination metadata
        page = (skip // limit) + 1 if limit > 0 else 1
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        pagination = PaginationMeta(
            total=total,
            skip=skip,
            limit=limit,
            page=page,
            total_pages=total_pages
        )
        
        elapsed = time.time() - start_time
        logger.info(f"get_auctions completed in {elapsed:.3f}s - {len(items_dto)} items returned")
        
        return AuctionListResponse(
            items=items_dto,
            pagination=pagination,
            filters={
                "status": status,
                "source": source,
                "asset_type": asset_type,
                "search": search
            }
        )
    
    def get_auction_by_lot_number(
        self, 
        lot_number: str, 
        source: Optional[str] = None
    ) -> Optional[AuctionDetailResponse]:
        """Get single auction by lot number and return detail DTO"""
        item = self.repository.get_by_lot_number(lot_number, source)
        
        if not item:
            return None
        
        return self._model_to_detail_dto(item)
    
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
        elif source == "state_dept":
            scraper = StateDeptScraper()
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
    
    def save_scraped_items(self, items: List[Dict]) -> int:
        """
        Save pre-scraped items to database.
        Used by scheduler when items are already scraped.
        
        Args:
            items: List of item dictionaries to save
            
        Returns:
            Number of items saved
        """
        if not items:
            return 0
        
        created_count = 0
        updated_count = 0
        
        for item_data in items:
            source = item_data.get("source", "unknown")
            lot_number = item_data.get("lot_number")
            
            if not lot_number:
                logger.warning(f"Skipping item without lot_number: {item_data}")
                continue
            
            try:
                existing = self.repository.get_by_lot_number(lot_number, source)
                
                if existing:
                    self.repository.update(existing, item_data)
                    updated_count += 1
                else:
                    self.repository.create(item_data)
                    created_count += 1
            except Exception as e:
                logger.error(f"Error saving item {lot_number}: {e}")
                continue
        
        total_saved = created_count + updated_count
        logger.info(f"Saved {total_saved} items ({created_count} created, {updated_count} updated)")
        
        return total_saved
    
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
    
    def _model_to_base_dto(self, item) -> AuctionBase:
        """Convert database model to base DTO for list views"""
        location = AuctionLocation(
            country=item.country,
            city=item.city,
            region=item.region,
            postal_code=item.postal_code,
            address_raw=item.address_raw
        )
        
        bidding = AuctionBidding(
            current_bid=item.current_bid,
            minimum_bid=item.minimum_bid,
            bid_increment=item.bid_increment,
            next_minimum_bid=item.next_minimum_bid,
            currency=item.currency,
            closing_date=item.closing_date,
            bid_date=item.bid_date
        )
        
        contact = AuctionContact(
            contact_name=item.contact_name,
            contact_phone=item.contact_phone,
            contact_email=item.contact_email
        )
        
        # Get first image URL
        first_image = None
        if item.image_urls:
            try:
                images = json.loads(item.image_urls)
                first_image = images[0] if images else None
            except:
                first_image = item.image_urls
        
        return AuctionBase(
            id=item.id,
            lot_number=item.lot_number,
            sale_number=item.sale_number,
            source=item.source,
            title=item.title,
            status=item.status,
            image_urls=first_image,
            agency=item.agency,
            asset_type=item.asset_type,
            location=location,
            bidding=bidding,
            contact=contact,
            is_available=item.is_available,
            item_url=item.item_url
        )
    
    def _model_to_detail_dto(self, item) -> AuctionDetailResponse:
        """Convert database model to detail DTO for single item view"""
        location = AuctionLocation(
            country=item.country,
            city=item.city,
            region=item.region,
            postal_code=item.postal_code,
            address_raw=item.address_raw
        )
        
        bidding = AuctionBidding(
            current_bid=item.current_bid,
            minimum_bid=item.minimum_bid,
            bid_increment=item.bid_increment,
            next_minimum_bid=item.next_minimum_bid,
            currency=item.currency,
            closing_date=item.closing_date,
            bid_date=item.bid_date
        )
        
        contact = AuctionContact(
            contact_name=item.contact_name,
            contact_phone=item.contact_phone,
            contact_email=item.contact_email
        )
        
        # Parse image URLs
        image_urls = []
        if item.image_urls:
            try:
                image_urls = json.loads(item.image_urls)
            except:
                image_urls = [item.image_urls] if item.image_urls else []
        
        # Parse extra data
        extra_data = {}
        if item.extra_data:
            try:
                extra_data = json.loads(item.extra_data)
            except:
                pass
        
        return AuctionDetailResponse(
            id=item.id,
            lot_number=item.lot_number,
            sale_number=item.sale_number,
            source=item.source,
            title=item.title,
            description=item.description,
            status=item.status,
            quantity=item.quantity,
            created_at=item.created_at,
            updated_at=item.updated_at,
            image_urls=image_urls,
            agency=item.agency,
            asset_type=item.asset_type,
            item_url=item.item_url,
            location=location,
            bidding=bidding,
            contact=contact,
            extra_data=extra_data,
            is_available=item.is_available
        )
    
    def _transform_to_api_format(self, item) -> Dict:
        """
        Transform database model to API response format (legacy method).
        Kept for backward compatibility with non-DTO endpoints.
        Use _model_to_base_dto or _model_to_detail_dto for new code.
        """
        return {
            "id": item.id,
            "lot_number": item.lot_number,
            "sale_number": item.sale_number,
            "source": item.source,
            "title": item.title,
            "description": item.description,
            "current_bid": float(item.current_bid) if item.current_bid else 0.0,
            "minimum_bid": float(item.minimum_bid) if item.minimum_bid else None,
            "bid_increment": float(item.bid_increment) if item.bid_increment else None,
            "next_minimum_bid": float(item.next_minimum_bid) if item.next_minimum_bid else None,
            "currency": item.currency,
            "quantity": item.quantity,
            "status": item.status,
            "is_available": item.is_available,
            "country": item.country,
            "city": item.city,
            "region": item.region,
            "postal_code": item.postal_code,
            "address_raw": item.address_raw,
            "closing_date": item.closing_date.isoformat() if item.closing_date else None,
            "bid_date": item.bid_date.isoformat() if item.bid_date else None,
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
