"""
Quick start script - Sets up and runs the FastAPI backend with minimal configuration.
Works out of the box with SQLite, upgrades to PostgreSQL when ready.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    try:
        import fastapi
        import sqlalchemy
        import requests
        import bs4
        print("✓ All dependencies installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependencies: {e}")
        print("\nInstalling dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True

def check_database():
    """Check database configuration"""
    print_header("Checking Database")
    
    db_url = os.getenv("DATABASE_URL")
    
    if db_url and "postgresql" in db_url:
        # Check if it's Neon
        if "neon.tech" in db_url:
            print(f"✓ Using Neon PostgreSQL (production-ready)")
            print(f"  Endpoint: {db_url.split('@')[1].split('/')[0] if '@' in db_url else 'hidden'}")
        else:
            print(f"✓ Using PostgreSQL: {db_url[:40]}...")
        return "postgresql"
    else:
        print("⚠ Using SQLite (local file database)")
        print("  This is fine for testing, but for production:")
        print("  1. Go to Neon dashboard → production branch")
        print("  2. Copy Connection String")
        print("  3. Add to .env file: DATABASE_URL=postgresql://...")
        print("  See NEON_SETUP.md for details")
        return "sqlite"

def initialize_database():
    """Initialize database tables"""
    print_header("Initializing Database")
    
    try:
        from core.database import init_db
        init_db()
        print("✓ Database tables created")
        return True
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        return False

def check_data_exists():
    """Check if any auction data exists"""
    print_header("Checking Data")
    
    try:
        from core.database import get_db
        from repositories import AuctionRepository
        
        db = next(get_db())
        repo = AuctionRepository(db)
        count = repo.count()
        
        if count > 0:
            print(f"✓ Database has {count} auction items")
            return True
        else:
            print("⚠ Database is empty - no auction data yet")
            print("  You can scrape data manually later or let the scheduler do it")
            return False
    except Exception as e:
        print(f"⚠ Could not check data: {e}")
        return False

def start_server():
    """Start the FastAPI server"""
    print_header("Starting FastAPI Server")
    
    print("Server will start on: http://localhost:8001")
    print("API Documentation: http://localhost:8001/docs")
    print("\nTo scrape data, run in another terminal:")
    print("  curl -X POST http://localhost:8001/api/scrape/all")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Start with or without scheduler based on availability
    try:
        from scheduler import start_scheduler
        print("✓ Starting with hourly auto-scraper...\n")
        scheduler = start_scheduler()
    except:
        print("⚠ Scheduler not available, running without auto-scraping\n")
        scheduler = None
    
    try:
        import uvicorn
        from main import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        if scheduler:
            scheduler.shutdown()
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        sys.exit(1)

def main():
    print_header("FastAPI Auction Scraper - Quick Start")
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Run checks and setup
    if not check_dependencies():
        print("\n✗ Failed to install dependencies")
        sys.exit(1)
    
    db_type = check_database()
    
    if not initialize_database():
        print("\n✗ Failed to initialize database")
        sys.exit(1)
    
    data_exists = check_data_exists()
    
    if not data_exists:
        print("\n💡 TIP: After server starts, scrape data with:")
        print("   curl -X POST http://localhost:8001/api/scrape/all")
        input("\nPress Enter to start server...")
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()
