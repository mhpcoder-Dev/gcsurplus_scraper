"""Test Neon database connection latency"""
from core.database import engine, SessionLocal
from sqlalchemy import text
import time

print("="*70)
print("NEON DATABASE LATENCY TEST")
print("="*70)

# Test 1: Connection pooling (should be fast after first connection)
print("\n1. Testing connection pooling...")
times = []
for i in range(5):
    start = time.time()
    conn = engine.connect()
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"   Connection {i+1}: {elapsed:.3f}s")
    conn.close()

avg = sum(times) / len(times)
print(f"   Average: {avg:.3f}s")

if avg > 1.0:
    print("   ⚠️ WARNING: Very high connection latency!")
    print("   This is causing your slow queries.")

# Test 2: Simple query through pool
print("\n2. Testing simple query...")
start = time.time()
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM auction_items"))
    count = result.scalar()
elapsed = time.time() - start
print(f"   Query time: {elapsed:.3f}s ({count} total rows)")

# Test 3: Query with LIMIT
print("\n3. Testing LIMIT query (24 rows)...")
start = time.time()
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM auction_items WHERE status = 'active' ORDER BY closing_date LIMIT 24"))
    rows = result.fetchall()
elapsed = time.time() - start
print(f"   Query time: {elapsed:.3f}s ({len(rows)} rows)")

# Test 4: Check if Neon is sleeping
print("\n4. Checking Neon status...")
print("   Neon free tier may have 'sleep after inactivity'")
print("   This adds 3-5 seconds to first query after sleep.")

# Test 5: Explain query plan
print("\n5. Checking if indexes are being used...")
with engine.connect() as conn:
    result = conn.execute(text("""
        EXPLAIN (ANALYZE, BUFFERS) 
        SELECT * FROM auction_items 
        WHERE status = 'active' 
        ORDER BY closing_date 
        LIMIT 24
    """))
    for row in result:
        print(f"   {row[0]}")

print("\n" + "="*70)
print("DIAGNOSIS:")
print("="*70)

if avg > 5.0:
    print("❌ CRITICAL: Connection time > 5s")
    print("   → Neon database is too slow from your location")
    print("   → Consider: Switch to local SQLite for development")
    print("   → Or: Use Neon only for production")
elif avg > 1.0:
    print("⚠️ HIGH LATENCY: Connection time > 1s")
    print("   → Neon might be sleeping (free tier)")
    print("   → Connection pooling should help")
else:
    print("✓ Connection latency is acceptable")
    print("   → Problem is elsewhere (query optimization needed)")

print("="*70)
