"""
Comment database model.
SQLAlchemy ORM model for user comments on auctions.
"""

from sqlalchemy import Column, String, Text, DateTime, Index
from datetime import datetime
from core.database import Base


class Comment(Base):
    """User comment on an auction item"""
    __tablename__ = "comments"
    
    # Composite indexes for common query patterns
    __table_args__ = (
        # Index for fetching comments by auction
        Index('idx_comment_auction', 'auction_id'),
        # Index for sorting by date
        Index('idx_comment_created', 'created_at'),
    )
    
    id = Column(String(255), primary_key=True)
    auction_id = Column(String(255), nullable=False, index=True)
    author = Column(String(100), default="Anonymous", nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<Comment(id='{self.id}', auction_id='{self.auction_id}', author='{self.author[:20]}')>"
