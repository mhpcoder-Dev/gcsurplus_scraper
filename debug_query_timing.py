"""
Debug query to see where time is spent
"""
import time
from core.database import SessionLocal
from repositories.auction_repository import AuctionRepository
from sqlalchemy import text

db = SessionLocal()
repo = AuctionRepository(db)

print("\n" + "="*70)
print("DETAILED QUERY TIMING BREAKDOWN")
print("="*70)

# Test 1: Raw SQL query
print("\n1. Raw SQL query (24 items)...")
start = time.time()
with db.connection() as conn:
    result = conn.execute(text("""
        SELECT id, lot_number, title, description, current_bid, status, source
        FROM auction_items 
        WHERE status = 'active' 
        ORDER BY closing_date 
        LIMIT 24
    """))
    rows = result.fetchall()
elapsed = time.time() - start
print(f"   Time: {elapsed:.3f}s ({len(rows)} rows)")
print(f"   Per row: {elapsed/len(rows)*1000:.1f}ms" if rows else "   No rows")

# Test 2: ORM query (full objects)
print("\n2. ORM query with full objects...")
start = time.time()
items = repo.get_all(skip=0, limit=24, status="active")
elapsed = time.time() - start
print(f"   Time: {elapsed:.3f}s ({len(items)} items)")
print(f"   Per item: {elapsed/len(items)*1000:.1f}ms" if items else "   No items")

# Test 3: Check if it's the transformation
print("\n3. Check data size...")
if items:
    item = items[0]
    print(f"   Title length: {len(item.title)} chars")
    print(f"   Description length: {len(item.description) if item.description else 0} chars")
    print(f"   Image URLs: {len(item.image_urls) if item.image_urls else 0} chars")
    
    # Estimate data size
    import sys
    size = sys.getsizeof(item.__dict__)
    print(f"   Object size: ~{size} bytes")
    print(f"   24 objects: ~{size * 24 / 1024:.1f} KB")

# Test 4: Connection latency test
print("\n4. Pure connection test...")
times = []
for i in range(3):
    start = time.time()
    with db.connection() as conn:
        result = conn.execute(text("SELECT 1"))
        result.fetchone()
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"   Ping {i+1}: {elapsed*1000:.0f}ms")
avg = sum(times) / len(times)
print(f"   Average: {avg*1000:.0f}ms")

print("\n" + "="*70)
print("ANALYSIS:")
print("="*70)

if avg > 0.5:
    print(f"\n⚠️ Network latency: {avg*1000:.0f}ms per query")
    print(f"   For 24 items, network overhead alone: {avg*24:.1f}s")
    print("\n   RECOMMENDATION: Switch to SQLite for development")
    print("   Run: python switch_database.py sqlite")
elif elapsed > 2:
    print("\n⚠️ Query is slow even with good network")
    print("   Check if indexes are being used:")
    print("   Run EXPLAIN ANALYZE on query")
else:
    print("\n✓ Performance is acceptable")

db.close()
