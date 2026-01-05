"""
Database migration script to update Neon database schema
Run this ONCE to update your Neon database to the new schema
"""

from sqlalchemy import text
from core.database import engine
from models.auction import Base

def migrate_database():
    """Update database schema to match new model"""
    
    print("Starting database migration...")
    
    with engine.connect() as conn:
        try:
            # Drop the old table if it exists
            print("Dropping old auction_items table...")
            conn.execute(text("DROP TABLE IF EXISTS auction_items CASCADE"))
            conn.commit()
            print("✓ Old table dropped")
            
        except Exception as e:
            print(f"\n✗ Error dropping table: {e}")
            conn.rollback()
    
    # Create new table with updated schema (outside transaction)
    try:
        print("Creating new auction_items table...")
        Base.metadata.create_all(bind=engine)
        print("✓ New table created with updated schema")
        
        print("\n✅ Migration complete!")
        print("Your Neon database is now ready to use.")
        print("\nNext step: Run scraper to populate data")
        print("  python start.py")
        
    except Exception as e:
        print(f"\n✗ Table creation failed: {e}")
        raise

if __name__ == "__main__":
    migrate_database()
