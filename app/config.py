from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""

    # Database - PostgreSQL for Vercel/cloud deployment
    # Free options: Neon (https://neon.tech), Supabase, Railway
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@host:5432/dbname"
    )

    # Scraping
    base_url: str = "https://www.gcsurplus.ca"
    listing_url: str = "https://www.gcsurplus.ca/mn-eng.cfm?snc=wfsav&sc=ach-shop&sr=1&vndsld=0&lci=&sf=aff-post&so=DESC"
    bid_api_url: str = "https://www.gcsurplus.ca/whatsforsale/Bid/Bid.cfc"
    scrape_interval_hours: int = 24

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
