"""
Database migration script to add country and category columns
Run this script once to update existing database schema
"""
from sqlalchemy import text
from app.database import engine, init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database():
    """Add new columns to existing database"""
    
    with engine.connect() as connection:
        try:
            # Add country column if it doesn't exist
            logger.info("Adding 'country' column...")
            connection.execute(text("""
                ALTER TABLE auction_items 
                ADD COLUMN IF NOT EXISTS country VARCHAR(50) DEFAULT 'Canada'
            """))
            connection.commit()
            
            # Create index on country
            logger.info("Creating index on 'country' column...")
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_auction_items_country 
                ON auction_items(country)
            """))
            connection.commit()
            
            # Add category column if it doesn't exist
            logger.info("Adding 'category' column...")
            connection.execute(text("""
                ALTER TABLE auction_items 
                ADD COLUMN IF NOT EXISTS category VARCHAR(100)
            """))
            connection.commit()
            
            # Create index on category
            logger.info("Creating index on 'category' column...")
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_auction_items_category 
                ON auction_items(category)
            """))
            connection.commit()
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            connection.rollback()
            raise


if __name__ == "__main__":
    logger.info("Starting database migration...")
    migrate_database()
    logger.info("Database migration completed!")
