"""
Comment Repository - Data Access Layer
Handles all database operations for comments.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from models.comment import Comment
import logging

logger = logging.getLogger(__name__)


class CommentRepository:
    """Repository for Comment database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_auction_id(self, auction_id: str) -> List[Comment]:
        """
        Get all comments for a specific auction.
        Returns comments sorted by newest first.
        """
        try:
            comments = self.db.query(Comment)\
                .filter(Comment.auction_id == auction_id)\
                .order_by(desc(Comment.created_at))\
                .all()
            return comments
        except Exception as e:
            logger.error(f"Error fetching comments for auction {auction_id}: {e}")
            return []
    
    def create(self, comment: Comment) -> Comment:
        """Create a new comment"""
        try:
            self.db.add(comment)
            self.db.commit()
            self.db.refresh(comment)
            return comment
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating comment: {e}")
            raise
    
    def delete(self, comment_id: str) -> bool:
        """Delete a comment by ID"""
        try:
            comment = self.db.query(Comment).filter(Comment.id == comment_id).first()
            if comment:
                self.db.delete(comment)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting comment {comment_id}: {e}")
            return False
    
    def get_by_id(self, comment_id: str) -> Optional[Comment]:
        """Get a single comment by ID"""
        try:
            return self.db.query(Comment).filter(Comment.id == comment_id).first()
        except Exception as e:
            logger.error(f"Error fetching comment {comment_id}: {e}")
            return None
    
    def get_count_by_auction(self, auction_id: str) -> int:
        """Get comment count for an auction"""
        try:
            return self.db.query(Comment)\
                .filter(Comment.auction_id == auction_id)\
                .count()
        except Exception as e:
            logger.error(f"Error counting comments for auction {auction_id}: {e}")
            return 0
