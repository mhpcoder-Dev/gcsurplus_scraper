"""
Comment Service - Business Logic Layer
Handles business logic and validation for comments.
"""

from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
import logging
import time
import random

from repositories.comment_repository import CommentRepository
from models.comment import Comment

logger = logging.getLogger(__name__)


class CommentService:
    """Service layer for comment business logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = CommentRepository(db)
    
    def get_comments(self, auction_id: str) -> List[Dict]:
        """
        Get all comments for an auction.
        Returns formatted comment data.
        """
        comments = self.repository.get_by_auction_id(auction_id)
        
        return [
            {
                "id": comment.id,
                "auctionId": comment.auction_id,
                "author": comment.author,
                "text": comment.text,
                "createdAt": comment.created_at.isoformat()
            }
            for comment in comments
        ]
    
    def create_comment(
        self, 
        auction_id: str, 
        text: str, 
        author: str = "Anonymous"
    ) -> Dict:
        """
        Create a new comment with validation.
        
        Args:
            auction_id: The auction lot number
            text: Comment text (1-1000 characters)
            author: Author name (optional, defaults to "Anonymous")
        
        Returns:
            Dict with comment data
        
        Raises:
            ValueError: If validation fails
        """
        # Validation
        if not auction_id or not auction_id.strip():
            raise ValueError("auction_id is required")
        
        if not text or not text.strip():
            raise ValueError("Comment text cannot be empty")
        
        text = text.strip()
        if len(text) > 1000:
            raise ValueError("Comment text cannot exceed 1000 characters")
        
        if len(text) < 1:
            raise ValueError("Comment text must be at least 1 character")
        
        # Sanitize author name
        author = (author or "Anonymous").strip()
        if len(author) > 100:
            author = author[:100]
        if not author:
            author = "Anonymous"
        
        # Generate unique ID
        comment_id = f"comment_{int(time.time() * 1000)}_{random.randint(100000, 999999)}"
        
        # Create comment
        comment = Comment(
            id=comment_id,
            auction_id=auction_id,
            author=author,
            text=text,
            created_at=datetime.utcnow()
        )
        
        created_comment = self.repository.create(comment)
        
        return {
            "id": created_comment.id,
            "auctionId": created_comment.auction_id,
            "author": created_comment.author,
            "text": created_comment.text,
            "createdAt": created_comment.created_at.isoformat()
        }
    
    def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a comment by ID.
        
        Args:
            comment_id: The comment ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        if not comment_id:
            return False
        
        return self.repository.delete(comment_id)
    
    def get_comment_count(self, auction_id: str) -> int:
        """Get the number of comments for an auction"""
        return self.repository.get_count_by_auction(auction_id)
