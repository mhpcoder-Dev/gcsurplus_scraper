from pydantic_settings import BaseSettings
from typing import Optional, Dict
import os
import pytz
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment-specific configuration support.
    
    Loads settings from:
    1. .env.common (common settings for all environments)
    2. .env.development OR .env.production (based on ENVIRONMENT variable)
    3. Environment variables (highest priority)
    """
    
    # Environment
    environment: str = "development"  # development, production, staging
    debug: bool = False

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

    # Scheduler Configuration
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"  # Can be overridden via .env
    run_initial_scrape: bool = False  # Run scrape immediately on startup
    
    # Site-specific scraping intervals (in hours)
    # Each site can have a different update frequency
    scraper_intervals: Dict[str, int] = {
        "gcsurplus": 24,    # Update GCSurplus every 24 hours
        "gsa": 12,          # Update GSA every 12 hours (more active)
        "treasury": 48,     # Update Treasury every 48 hours (less frequent updates)
        "state_dept": 24    # Update State Dept every 24 hours
    }
    
    # Optional: Set specific times for scraping (24-hour format)
    # If not set, will use intervals instead
    scraper_schedule_times: Dict[str, str] = {
        # Examples:
        # "gcsurplus": "02:00",  # Run at 2:00 AM
        # "gsa": "01:00,13:00",  # Run at 1:00 AM and 1:00 PM
    }
    
    # Frontend URL (for CORS)
    frontend_url: Optional[str] = None
    
    # Security
    api_key: Optional[str] = None  # For protected endpoints
    secret_key: Optional[str] = None  # For JWT tokens (future use)

    class Config:
        case_sensitive = False
        
        @staticmethod
        def customise_sources(
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            """
            Customize settings sources to load from multiple env files.
            Priority (highest to lowest):
            1. Environment variables
            2. .env.{environment} (e.g., .env.production)
            3. .env.common
            4. Default values
            """
            from pydantic_settings import (
                EnvSettingsSource,
                InitSettingsSource,
                DotEnvSettingsSource,
            )
            
            # Get environment from env var or default to development
            environment = os.getenv("ENVIRONMENT", "development")
            
            # Define file paths
            common_env_file = Path(".env.common")
            env_specific_file = Path(f".env.{environment}")
            
            sources = [
                init_settings,
                # Environment variables (highest priority)
                EnvSettingsSource(Settings),
            ]
            
            # Add environment-specific env file if it exists
            if env_specific_file.exists():
                sources.append(
                    DotEnvSettingsSource(
                        Settings,
                        env_file=env_specific_file,
                        env_file_encoding='utf-8'
                    )
                )
            
            # Add common env file if it exists
            if common_env_file.exists():
                sources.append(
                    DotEnvSettingsSource(
                        Settings,
                        env_file=common_env_file,
                        env_file_encoding='utf-8'
                    )
                )
            
            return tuple(sources)


def get_settings() -> Settings:
    """Get settings instance with proper environment loading"""
    return Settings()


settings = get_settings()

