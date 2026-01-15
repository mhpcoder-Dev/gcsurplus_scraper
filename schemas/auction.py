"""
Auction DTO schemas for API responses.
Controls exactly what data is sent to the frontend.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class AuctionLocation(BaseModel):
    """Location information for an auction item"""
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    address_raw: Optional[str] = None
    
    class Config:
        from_attributes = True


class AuctionBidding(BaseModel):
    """Bidding information for an auction item"""
    current_bid: Optional[Decimal] = Field(None, description="Current bid amount")
    minimum_bid: Optional[Decimal] = Field(None, description="Minimum bid amount")
    bid_increment: Optional[Decimal] = Field(None, description="Bid increment")
    next_minimum_bid: Optional[Decimal] = Field(None, description="Next minimum bid")
    currency: str = Field(default="USD", description="Currency code")
    
    @validator('current_bid', 'minimum_bid', 'bid_increment', 'next_minimum_bid', pre=True)
    def convert_to_float(cls, v):
        """Convert Decimal to float for JSON serialization"""
        if v is None:
            return None
        return float(v) if isinstance(v, Decimal) else v
    
    class Config:
        from_attributes = True


class AuctionBase(BaseModel):
    """Base auction fields for list view (minimal data)"""
    id: int
    lot_number: str
    sale_number: Optional[str] = None
    source: str
    title: str
    status: str
    closing_date: Optional[datetime] = None
    image_urls: Optional[str] = None  # First image or JSON string
    agency: Optional[str] = None
    asset_type: Optional[str] = None
    
    # Embedded objects
    location: Optional[AuctionLocation] = None
    bidding: Optional[AuctionBidding] = None
    
    # Computed fields
    is_available: bool = True
    item_url: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @validator('image_urls', pre=True)
    def extract_first_image(cls, v):
        """Extract first image URL if JSON array"""
        if not v:
            return None
        if isinstance(v, str):
            # Try to parse as JSON and get first image
            import json
            try:
                images = json.loads(v)
                return images[0] if images else None
            except:
                return v
        return v


class AuctionDetailResponse(BaseModel):
    """Detailed auction response for single item view"""
    id: int
    lot_number: str
    sale_number: Optional[str] = None
    source: str
    title: str
    description: Optional[str] = None
    status: str
    quantity: Optional[int] = 1
    
    # Dates
    closing_date: Optional[datetime] = None
    bid_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Images (full array)
    image_urls: Optional[List[str]] = None
    
    # Contact
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    
    # Agency/Organization
    agency: Optional[str] = None
    asset_type: Optional[str] = None
    
    # URL
    item_url: Optional[str] = None
    
    # Embedded objects
    location: Optional[AuctionLocation] = None
    bidding: Optional[AuctionBidding] = None
    
    # Extra data (parsed JSON)
    extra_data: Optional[Dict[str, Any]] = None
    
    # Computed
    is_available: bool = True
    
    class Config:
        from_attributes = True
    
    @validator('image_urls', pre=True)
    def parse_image_urls(cls, v):
        """Parse image URLs from JSON string"""
        if not v:
            return []
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return [v]
        return v
    
    @validator('extra_data', pre=True)
    def parse_extra_data(cls, v):
        """Parse extra_data from JSON string"""
        if not v:
            return {}
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return {}
        return v


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int
    skip: int
    limit: int
    page: int
    total_pages: int


class AuctionListResponse(BaseModel):
    """Paginated auction list response"""
    items: List[AuctionBase]
    pagination: PaginationMeta
    filters: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
