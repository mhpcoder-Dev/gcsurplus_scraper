"""
Main entry point for running the FastAPI application with scheduler.
"""

import uvicorn
from main import app
from scheduler import start_scheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    # Start the scheduler for hourly updates
    scheduler = start_scheduler()
    logger.info("Starting FastAPI application with scheduler...")
    
    try:
        # Run the FastAPI application
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.shutdown()
