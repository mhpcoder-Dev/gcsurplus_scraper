"""
Comment DTO schemas for API responses.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class CommentCreate(BaseModel):
    """Request model for creating a comment"""
    auctionId: str
    text: str
    author: Optional[str] = "Anonymous"
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Comment text cannot be empty')
        if len(v) > 1000:
            raise ValueError('Comment text cannot exceed 1000 characters')
        return v.strip()
    
    @validator('auctionId')
    def validate_auction_id(cls, v):
        if not v or not v.strip():
            raise ValueError('auctionId is required')
        return v.strip()
    
    @validator('author')
    def validate_author(cls, v):
        if v and len(v) > 100:
            return v[:100]
        return v or "Anonymous"


class CommentResponse(BaseModel):
    """Response model for a comment"""
    id: str
    auctionId: str = Field(..., alias='auction_id')
    text: str
    author: str
    createdAt: datetime = Field(..., alias='created_at')
    
    class Config:
        from_attributes = True
        populate_by_name = True


class CommentListResponse(BaseModel):
    """Response model for list of comments"""
    comments: List[CommentResponse]
    total: int
