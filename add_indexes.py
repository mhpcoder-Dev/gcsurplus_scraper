"""
Add Performance Indexes to Auction Items Table
Run this script to add composite indexes for faster queries
"""

import sys
import logging
from sqlalchemy import text

from core.database import engine, init_db
from models.auction import Base, AuctionItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_indexes():
    """Add composite indexes to speed up queries"""
    
    logger.info("Starting index creation...")
    
    with engine.connect() as conn:
        # Check if we're using PostgreSQL or SQLite
        dialect = engine.dialect.name
        logger.info(f"Database dialect: {dialect}")
        
        indexes_to_create = [
            ("idx_status_closing", "CREATE INDEX IF NOT EXISTS idx_status_closing ON auction_items (status, closing_date)"),
            ("idx_source_status_closing", "CREATE INDEX IF NOT EXISTS idx_source_status_closing ON auction_items (source, status, closing_date)"),
            ("idx_asset_status_closing", "CREATE INDEX IF NOT EXISTS idx_asset_status_closing ON auction_items (asset_type, status, closing_date)"),
            ("idx_filters", "CREATE INDEX IF NOT EXISTS idx_filters ON auction_items (status, source, asset_type)"),
        ]
        
        for idx_name, idx_sql in indexes_to_create:
            try:
                logger.info(f"Creating index: {idx_name}")
                conn.execute(text(idx_sql))
                conn.commit()
                logger.info(f"✓ Index {idx_name} created successfully")
            except Exception as e:
                logger.warning(f"Index {idx_name} might already exist or failed: {e}")
        
        # Analyze table for better query planning (PostgreSQL only)
        if dialect == 'postgresql':
            try:
                logger.info("Running ANALYZE on auction_items table...")
                conn.execute(text("ANALYZE auction_items"))
                conn.commit()
                logger.info("✓ ANALYZE completed")
            except Exception as e:
                logger.warning(f"ANALYZE failed: {e}")
        
        # Vacuum analyze for SQLite
        if dialect == 'sqlite':
            try:
                logger.info("Running ANALYZE for SQLite...")
                conn.execute(text("ANALYZE"))
                conn.commit()
                logger.info("✓ ANALYZE completed")
            except Exception as e:
                logger.warning(f"ANALYZE failed: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("Index creation completed!")
    logger.info("Your queries should now be significantly faster.")
    logger.info("="*60)

def check_index_usage():
    """Check if indexes exist and their sizes"""
    
    logger.info("\nChecking existing indexes...")
    
    with engine.connect() as conn:
        dialect = engine.dialect.name
        
        if dialect == 'postgresql':
            # PostgreSQL: Show all indexes on auction_items
            result = conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'auction_items'
                ORDER BY indexname
            """))
            
            logger.info("\nExisting indexes on auction_items:")
            for row in result:
                logger.info(f"  - {row[0]}")
        
        elif dialect == 'sqlite':
            # SQLite: Show all indexes
            result = conn.execute(text("""
                SELECT name, sql 
                FROM sqlite_master 
                WHERE type = 'index' AND tbl_name = 'auction_items'
                ORDER BY name
            """))
            
            logger.info("\nExisting indexes on auction_items:")
            for row in result:
                if row[1]:  # Skip auto-indexes (they have NULL sql)
                    logger.info(f"  - {row[0]}")

if __name__ == "__main__":
    try:
        # First check existing indexes
        check_index_usage()
        
        # Add new indexes
        add_indexes()
        
        # Check again to confirm
        check_index_usage()
        
        logger.info("\n✓ Database optimization complete!")
        logger.info("You should see dramatically faster query times now.")
        
    except Exception as e:
        logger.error(f"Error during index creation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
