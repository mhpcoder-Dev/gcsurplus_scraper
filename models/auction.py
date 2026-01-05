"""
Auction item database model.
SQLAlchemy ORM model definition.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from datetime import datetime
from core.database import Base


class AuctionItem(Base):
    """Unified auction item database model for all sources (GCSurplus, GSA, etc.)"""
    __tablename__ = "auction_items"
    
    # Composite indexes for common query patterns
    __table_args__ = (
        # Index for status + closing_date ordering (most common query)
        Index('idx_status_closing', 'status', 'closing_date'),
        # Index for source + status + closing_date
        Index('idx_source_status_closing', 'source', 'status', 'closing_date'),
        # Index for asset_type + status + closing_date
        Index('idx_asset_status_closing', 'asset_type', 'status', 'closing_date'),
        # Index for status + source + asset_type (for counts)
        Index('idx_filters', 'status', 'source', 'asset_type'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # Unique identifier combining source and lot number
    lot_number = Column(String(100), unique=True, index=True, nullable=False)
    sale_number = Column(String(100), index=True)
    source = Column(String(50), index=True, nullable=False)  # 'gcsurplus', 'gsa', etc.
    
    # Basic info
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Bidding info
    current_bid = Column(Float, default=0.0)
    minimum_bid = Column(Float)
    bid_increment = Column(Float)
    next_minimum_bid = Column(Float)
    
    # Status
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="active", index=True)  # active, closed, expired, upcoming
    is_available = Column(Boolean, default=True, index=True)
    
    # Location (support both Canadian provinces and US states)
    location_city = Column(String(200))
    location_province = Column(String(100))  # For Canadian items
    location_state = Column(String(100))      # For US items
    location_address = Column(Text)
    
    # Dates
    closing_date = Column(DateTime, index=True)
    bid_date = Column(DateTime)
    time_remaining = Column(String(100))
    
    # Images
    image_urls = Column(Text)  # JSON string of image URLs
    
    # Contact
    contact_name = Column(String(200))
    contact_phone = Column(String(50))
    contact_email = Column(String(200))
    
    # Agency/Organization
    agency = Column(String(200))
    asset_type = Column(String(50), index=True)  # 'cars', 'real-estate', 'electronics', etc.
    
    # Item URL
    item_url = Column(String(500))
    
    # Extra data (JSON) for source-specific fields
    extra_data = Column(Text)  # JSON string for flexible additional data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AuctionItem(lot_number='{self.lot_number}', source='{self.source}', title='{self.title[:50]}')>"
