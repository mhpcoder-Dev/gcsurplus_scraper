from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

# Create PostgreSQL database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AuctionItem(Base):
    """Auction item database model"""
    __tablename__ = "auction_items"

    id = Column(Integer, primary_key=True, index=True)
    lot_number = Column(String(100), unique=True, index=True, nullable=False)
    sale_number = Column(String(100), index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Bidding info
    current_bid = Column(Float, default=0.0)
    minimum_bid = Column(Float)
    bid_increment = Column(Float)
    next_minimum_bid = Column(Float)
    
    # Status
    quantity = Column(Integer)
    status = Column(String(20), default="active")  # active, closed, expired
    is_available = Column(Boolean, default=True)
    
    # Location
    location_city = Column(String(200))
    location_province = Column(String(100))
    location_address = Column(Text)
    
    # Dates
    closing_date = Column(DateTime)
    bid_date = Column(DateTime)
    time_remaining = Column(String(100))
    
    # Images
    image_urls = Column(Text)  # JSON string of image URLs
    
    # Contact
    contact_name = Column(String(200))
    contact_phone = Column(String(50))
    contact_email = Column(String(200))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
