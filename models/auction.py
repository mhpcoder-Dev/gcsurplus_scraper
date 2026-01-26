"""
Auction item database model.
SQLAlchemy ORM model definition.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index, Numeric
from datetime import datetime
from core.database import Base


# 1. Grouping Bidding Data
class BiddingMixin:
    """Mixin for bidding-related fields"""
    # Use Numeric(12, 2) instead of Float for money to avoid precision issues
    current_bid = Column(Numeric(12, 2), default=0.0)
    minimum_bid = Column(Numeric(12, 2))
    bid_increment = Column(Numeric(12, 2))
    next_minimum_bid = Column(Numeric(12, 2))
    currency = Column(String(10), default="USD") # Essential for multi-country scraping
    # Dates (stored in UTC timezone)
    closing_date = Column(DateTime, index=True)  # UTC timezone
    bid_date = Column(DateTime)  # UTC timezone


# 2. Grouping Location Data
class LocationMixin:
    """Mixin for location-related fields"""
    country = Column(String(100), index=True)
    city = Column(String(200), index=True)
    region = Column(String(100)) # Can be State, Province, or Territory
    postal_code = Column(String(20))
    address_raw = Column(Text) # Original unparsed address string from scraper


# 3. Grouping Contact Data
class ContactMixin:
    """Mixin for contact-related fields"""
    contact_name = Column(String(200))
    contact_phone = Column(String(50))
    contact_email = Column(String(200))


class AuctionItem(Base, BiddingMixin, LocationMixin, ContactMixin):
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
    
    # Status/Stock
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="active", index=True)  # active, closed, expired, upcoming
    is_available = Column(Boolean, default=True, index=True)
    
    # Images
    image_urls = Column(Text)  # JSON string of image URLs
    
    # Agency/Organization
    agency = Column(String(200))
    asset_type = Column(String(50), index=True)  # 'cars', 'real-estate', 'electronics', etc.
    
    # Item URL
    item_url = Column(String(1000))
    
    # Extra data (JSON) for source-specific fields
    extra_data = Column(Text)  # JSON string for flexible additional data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AuctionItem(lot_number='{self.lot_number}', source='{self.source}', title='{self.title[:50]}')>"
