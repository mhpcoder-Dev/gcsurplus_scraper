"""
Auction Repository - Data Access Layer
Handles all direct database operations for auction items.
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import json
import logging

from models.auction import AuctionItem

logger = logging.getLogger(__name__)


class AuctionRepository:
    """
    Repository pattern for AuctionItem data access.
    Encapsulates all database queries and operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, item_data: Dict) -> AuctionItem:
        """Create a new auction item"""
        # Convert lists/dicts to JSON strings
        if 'image_urls' in item_data and isinstance(item_data['image_urls'], list):
            item_data['image_urls'] = json.dumps(item_data['image_urls'])
        
        if 'extra_data' in item_data and isinstance(item_data['extra_data'], dict):
            item_data['extra_data'] = json.dumps(item_data['extra_data'])
        
        new_item = AuctionItem(**item_data)
        self.db.add(new_item)
        self.db.commit()
        self.db.refresh(new_item)
        return new_item
    
    def update(self, item: AuctionItem, item_data: Dict) -> AuctionItem:
        """Update an existing auction item"""
        # Convert lists/dicts to JSON strings
        if 'image_urls' in item_data and isinstance(item_data['image_urls'], list):
            item_data['image_urls'] = json.dumps(item_data['image_urls'])
        
        if 'extra_data' in item_data and isinstance(item_data['extra_data'], dict):
            item_data['extra_data'] = json.dumps(item_data['extra_data'])
        
        for key, value in item_data.items():
            setattr(item, key, value)
        
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def get_by_lot_number(
        self, 
        lot_number: str, 
        source: Optional[str] = None
    ) -> Optional[AuctionItem]:
        """Get auction item by lot number and optionally source"""
        query = self.db.query(AuctionItem).filter(AuctionItem.lot_number == lot_number)
        
        if source:
            query = query.filter(AuctionItem.source == source)
        
        return query.first()
    
    def get_by_id(self, item_id: int) -> Optional[AuctionItem]:
        """Get auction item by ID"""
        return self.db.query(AuctionItem).filter(AuctionItem.id == item_id).first()
    
    def get_upcoming(
        self,
        skip: int = 0,
        limit: int = 50,
        source: Optional[str] = None,
        asset_type: Optional[str] = None
    ) -> List[AuctionItem]:
        """Get upcoming auction items (status='upcoming', like Treasury.gov auctions)"""
        query = self.db.query(AuctionItem).filter(AuctionItem.status == "upcoming")
        
        if source:
            query = query.filter(AuctionItem.source == source)
        
        if asset_type:
            query = query.filter(AuctionItem.asset_type == asset_type)
        
        # Order by closing date (auction date)
        query = query.order_by(AuctionItem.closing_date.asc().nullslast())
        
        return query.offset(skip).limit(limit).all()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        source: Optional[str] = None,
        asset_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[AuctionItem]:
        """Get all auction items with filters - optimized with composite indexes"""
        import time
        start_time = time.time()
        
        query = self.db.query(AuctionItem)
        
        # Apply filters in order of selectivity (most selective first)
        # This helps the query planner use the best index
        if status:
            query = query.filter(AuctionItem.status == status)
            
            # If status is 'active', only return auctions that haven't ended yet
            # This handles timezone conversion issues from USA sites
            if status == 'active':
                query = query.filter(
                    or_(
                        AuctionItem.closing_date.is_(None),
                        AuctionItem.closing_date >= datetime.utcnow()
                    )
                )
        
        if source:
            query = query.filter(AuctionItem.source == source)
        
        if asset_type:
            # Support multiple asset types separated by comma
            asset_types = [at.strip() for at in asset_type.split(',')]
            if len(asset_types) > 1:
                query = query.filter(AuctionItem.asset_type.in_(asset_types))
            else:
                query = query.filter(AuctionItem.asset_type == asset_types[0])
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    AuctionItem.title.ilike(search_term),
                    AuctionItem.description.ilike(search_term),
                    AuctionItem.city.ilike(search_term),
                    AuctionItem.country.ilike(search_term),
                    AuctionItem.region.ilike(search_term),
                    AuctionItem.agency.ilike(search_term)
                )
            )
        
        # Order by closing date (uses composite index)
        query = query.order_by(AuctionItem.closing_date.asc().nullslast())
        
        result = query.offset(skip).limit(limit).all()
        
        elapsed = time.time() - start_time
        logger.info(f"Query completed in {elapsed:.3f}s - returned {len(result)} items (skip={skip}, limit={limit})")
        
        return result
    
    def count(
        self,
        status: Optional[str] = None,
        source: Optional[str] = None,
        asset_type: Optional[str] = None
    ) -> int:
        """Get count of items matching filters - optimized with indexed columns"""
        from sqlalchemy import func
        
        # Use func.count() which is faster than query.count()
        query = self.db.query(func.count(AuctionItem.id))
        
        if source:
            query = query.filter(AuctionItem.source == source)
        
        if status:
            query = query.filter(AuctionItem.status == status)
            
            # If status is 'active', only count auctions that haven't ended yet
            # This ensures pagination metadata matches the filtered results
            if status == 'active':
                query = query.filter(
                    or_(
                        AuctionItem.closing_date.is_(None),
                        AuctionItem.closing_date >= datetime.utcnow()
                    )
                )
        
        if asset_type:
            # Support multiple asset types separated by comma
            asset_types = [at.strip() for at in asset_type.split(',')]
            if len(asset_types) > 1:
                query = query.filter(AuctionItem.asset_type.in_(asset_types))
            else:
                query = query.filter(AuctionItem.asset_type == asset_types[0])
        
        return query.scalar()
    
    def mark_unavailable(
        self, 
        current_lot_numbers: List[str], 
        source: str
    ) -> int:
        """Mark items as closed if not in current listing"""
        updated_count = self.db.query(AuctionItem).filter(
            and_(
                AuctionItem.source == source,
                AuctionItem.lot_number.notin_(current_lot_numbers),
                AuctionItem.status == "active"
            )
        ).update(
            {"status": "closed", "is_available": False}, 
            synchronize_session=False
        )
        
        self.db.commit()
        return updated_count
    
    def delete_old(self, days: int = 0) -> int:
        """Delete closed/expired items older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = self.db.query(AuctionItem).filter(
            AuctionItem.status.in_(["closed", "expired"]),
            AuctionItem.updated_at < cutoff_date
        ).delete(synchronize_session=False)
        
        self.db.commit()
        return deleted_count
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        total = self.db.query(AuctionItem).count()
        active = self.db.query(AuctionItem).filter(AuctionItem.status == "active").count()
        upcoming = self.db.query(AuctionItem).filter(AuctionItem.status == "upcoming").count()
        closed = self.db.query(AuctionItem).filter(AuctionItem.status == "closed").count()
        expired = self.db.query(AuctionItem).filter(AuctionItem.status == "expired").count()
        
        # Count by source (include both active and upcoming)
        sources = {}
        for source_name in ['gcsurplus', 'gsa', 'treasury', 'state_dept']:
            source_count = self.db.query(AuctionItem).filter(
                AuctionItem.source == source_name,
                or_(AuctionItem.status == "active", AuctionItem.status == "upcoming")
            ).count()
            sources[source_name] = source_count
        
        return {
            "total_items": total,
            "active_auctions": active,
            "upcoming_auctions": upcoming,
            "closed_auctions": closed,
            "expired_auctions": expired,
            "by_source": sources
        }
