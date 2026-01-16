from pydantic_settings import BaseSettings
import os
from functools import lru_cache


def get_env_file():
    env = os.getenv("APP_ENV", "development")
    return [
        "../.env",
        f"../.env.{env}"
    ]

class Settings(BaseSettings):
    database_url: str 
    gsa_api_key: str
    base_url: str
    api_port: int
    api_host: str
    log_level: str
    debug: bool

    # Frontend URL (for CORS)
    frontend_url: str
    scheduler_enabled: bool
    run_initial_scrape: bool
    delete_closed_immediately: bool
    api_key: str
    secret_key: str

    # Database Connection Pool
    db_pool_size: int
    db_max_overflow: int
    db_pool_pre_ping: bool

    # Scraping URLs
    listing_url: str
    bid_api_url: str

    # GSA API Configuration
    gsa_api_base_url: str

    # Treasury.gov Configuration
    treasury_base_url: str
    treasury_listing_url: str

    # Request Settings
    request_timeout: int
    max_retries: int

    # Scheduler Configuration
    scheduler_timezone: str

    # Scraper Intervals (in hours)
    scraper_interval_gcsurplus: int
    scraper_interval_gsa: int
    scraper_interval_treasury: int
    scraper_interval_state_dept: int
    scrape_interval_hours: int


    class config:
        env_file = get_env_file()
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings():
    settings = Settings()
    return settings