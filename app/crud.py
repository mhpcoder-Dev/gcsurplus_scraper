from sqlalchemy.orm import Session
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
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None
) -> List[AuctionItem]:
    """
    Get all auction items with optional filters.
    """
    query = db.query(AuctionItem).order_by(AuctionItem.updated_at.desc())
    
    if status:
        query = query.filter(AuctionItem.status == status)
    
    if country:
        query = query.filter(AuctionItem.country == country)
    
    if category:
        query = query.filter(AuctionItem.category.ilike(f"%{category}%"))
    
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
    Get database statistics including country and category breakdowns.
    """
    total = db.query(AuctionItem).count()
    active = db.query(AuctionItem).filter(AuctionItem.status == "active").count()
    closed = db.query(AuctionItem).filter(AuctionItem.status == "closed").count()
    expired = db.query(AuctionItem).filter(AuctionItem.status == "expired").count()
    
    # Get country breakdown
    canada_count = db.query(AuctionItem).filter(AuctionItem.country == "Canada").count()
    usa_count = db.query(AuctionItem).filter(AuctionItem.country == "USA").count()
    
    # Get category breakdown (top categories)
    from sqlalchemy import func
    categories = db.query(
        AuctionItem.category, 
        func.count(AuctionItem.id).label('count')
    ).group_by(AuctionItem.category).order_by(func.count(AuctionItem.id).desc()).all()
    
    category_stats = {cat: count for cat, count in categories if cat}
    
    return {
        "total_items": total,
        "active_auctions": active,
        "closed_auctions": closed,
        "expired_auctions": expired,
        "by_country": {
            "Canada": canada_count,
            "USA": usa_count
        },
        "by_category": category_stats
    }
