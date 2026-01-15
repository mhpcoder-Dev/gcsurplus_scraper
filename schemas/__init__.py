"""
DTO (Data Transfer Object) schemas for API responses.
Using Pydantic for validation and serialization.
"""

from .auction import (
    AuctionListResponse,
    AuctionDetailResponse,
    AuctionBase,
    AuctionLocation,
    AuctionBidding,
    PaginationMeta
)
from .comment import (
    CommentResponse,
    CommentCreate,
    CommentListResponse
)

__all__ = [
    # Auction DTOs
    "AuctionListResponse",
    "AuctionDetailResponse",
    "AuctionBase",
    "AuctionLocation",
    "AuctionBidding",
    "PaginationMeta",
    # Comment DTOs
    "CommentResponse",
    "CommentCreate",
    "CommentListResponse",
]
