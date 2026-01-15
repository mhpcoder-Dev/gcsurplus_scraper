"""
Database Migration Script: Update schema to match refactored model with Mixins
Automatically runs SQL migration against the configured database
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the schema migration"""
    
    # Read SQL migration file
    sql_file = Path(__file__).parent / "migrate_schema_to_mixins.sql"
    if not sql_file.exists():
        logger.error(f"Migration file not found: {sql_file}")
        return False
    
    with open(sql_file, 'r') as f:
        migration_sql = f.read()
    
    logger.info(f"Connecting to database: {settings.database_url[:30]}...")
    
    try:
        # Create engine
        engine = create_engine(settings.database_url)
        
        # Check if it's PostgreSQL
        if "sqlite" in settings.database_url.lower():
            logger.error("❌ This migration is for PostgreSQL only!")
            logger.error("SQLite doesn't support the advanced ALTER TABLE operations needed.")
            logger.error("Please switch to PostgreSQL (Neon) database.")
            return False
        
        # Execute migration
        logger.info("Running migration...")
        with engine.connect() as connection:
            # Execute as a single transaction
            try:
                result = connection.execute(text(migration_sql))
                connection.commit()
                logger.info("Migration executed successfully")
            except Exception as e:
                logger.error(f"Migration error: {e}")
                connection.rollback()
                raise
        
        logger.info("✅ Migration completed successfully!")
        
        # Verify schema
        logger.info("\nVerifying schema...")
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'auction_items' 
                ORDER BY ordinal_position
            """))
            
            logger.info("\nCurrent schema:")
            logger.info("-" * 70)
            for row in result:
                logger.info(f"  {row[0]:30} {row[1]:20} {'NULL' if row[2] == 'YES' else 'NOT NULL'}")
            logger.info("-" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Database Schema Migration: Add BiddingMixin & LocationMixin columns")
    logger.info("=" * 70)
    
    if run_migration():
        logger.info("\n✅ Migration successful! Restart your FastAPI server.")
    else:
        logger.error("\n❌ Migration failed! Check errors above.")
        sys.exit(1)
