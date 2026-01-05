from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with smart defaults"""

    # Database - Neon PostgreSQL recommended, SQLite fallback for quick testing
    database_url: str = "sqlite:///./auction_data.db"  # Default, overridden by .env
    
    # Connection pool settings for PostgreSQL/Neon
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True  # Important for Neon to handle connection issues

    # Scraping
    base_url: str = "https://www.gcsurplus.ca"
    listing_url: str = "https://www.gcsurplus.ca/mn-eng.cfm?snc=wfsav&sc=ach-shop&sr=1&vndsld=0&lci=&sf=aff-post&so=DESC"
    bid_api_url: str = "https://www.gcsurplus.ca/whatsforsale/Bid/Bid.cfc"
    scrape_interval_hours: int = 24

    # GSA API
    gsa_api_key: str = "rXyfDnTjMh3d0Zu56fNcMbHb5dgFBQrmzfTjZqq3"
    gsa_api_base_url: str = "https://api.gsa.gov/assets/gsaauctions/v2"

    # Treasury.gov Real Property Auctions
    treasury_base_url: str = "https://www.treasury.gov/auctions/treasury/rp"
    treasury_listing_url: str = "https://www.treasury.gov/auctions/treasury/rp/realprop.shtml"

    # API
    api_port: int = 8001
    api_host: str = "0.0.0.0"

    # Logging
    log_level: str = "INFO"

    # Request settings
    request_timeout: int = 30
    max_retries: int = 3
    
    # Cleanup - keep only active auctions for free tier
    delete_closed_immediately: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
