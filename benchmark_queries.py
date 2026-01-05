"""
Quick performance test to compare query speeds
Run this BEFORE and AFTER adding indexes to see the improvement
"""

import time
import sys
from sqlalchemy.orm import Session

from core.database import SessionLocal, init_db
from repositories.auction_repository import AuctionRepository

def benchmark_query(description, func, *args, **kwargs):
    """Run a query and measure execution time"""
    print(f"\n{description}...")
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    
    count = len(result) if isinstance(result, list) else result
    print(f"  ✓ {count} results in {elapsed:.3f}s")
    return elapsed

def run_benchmarks():
    """Run performance benchmarks"""
    
    print("="*70)
    print("DATABASE PERFORMANCE BENCHMARK")
    print("="*70)
    
    db: Session = SessionLocal()
    repo = AuctionRepository(db)
    
    try:
        # Test 1: Simple filter (most common)
        t1 = benchmark_query(
            "Test 1: Get active auctions (page 1, 24 items)",
            repo.get_all,
            skip=0,
            limit=24,
            status="active"
        )
        
        # Test 2: Count query
        t2 = benchmark_query(
            "Test 2: Count active auctions",
            repo.count,
            status="active"
        )
        
        # Test 3: Multi-filter
        t3 = benchmark_query(
            "Test 3: Get active auctions from gcsurplus",
            repo.get_all,
            skip=0,
            limit=24,
            status="active",
            source="gcsurplus"
        )
        
        # Test 4: Pagination deep
        t4 = benchmark_query(
            "Test 4: Get page 7 (skip=144)",
            repo.get_all,
            skip=144,
            limit=24,
            status="active"
        )
        
        # Test 5: Asset type filter
        t5 = benchmark_query(
            "Test 5: Get vehicles",
            repo.get_all,
            skip=0,
            limit=24,
            status="active",
            asset_type="vehicles"
        )
        
        # Test 6: Search query (expensive)
        t6 = benchmark_query(
            "Test 6: Search for 'car'",
            repo.get_all,
            skip=0,
            limit=24,
            status="active",
            search="car"
        )
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        total_time = t1 + t2 + t3 + t4 + t5 + t6
        print(f"Total time for 6 queries: {total_time:.3f}s")
        print(f"Average query time: {total_time/6:.3f}s")
        
        # Performance targets
        print("\n" + "="*70)
        print("PERFORMANCE TARGETS")
        print("="*70)
        
        targets = {
            "Simple filter (Test 1)": (t1, 0.5, "CRITICAL"),
            "COUNT query (Test 2)": (t2, 0.2, "HIGH"),
            "Multi-filter (Test 3)": (t3, 0.5, "HIGH"),
            "Deep pagination (Test 4)": (t4, 0.5, "MEDIUM"),
            "Asset filter (Test 5)": (t5, 0.5, "MEDIUM"),
            "Search query (Test 6)": (t6, 1.0, "LOW")
        }
        
        print("\nTest                           Time    Target   Status")
        print("-" * 70)
        
        passed = 0
        total = len(targets)
        
        for test_name, (actual, target, priority) in targets.items():
            status = "✓ PASS" if actual <= target else "✗ SLOW"
            color = "" if actual <= target else "⚠️ "
            print(f"{color}{test_name:30} {actual:6.3f}s  {target:5.2f}s   {status}")
            if actual <= target:
                passed += 1
        
        print("-" * 70)
        print(f"Score: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 EXCELLENT! All queries meet performance targets!")
        elif passed >= total * 0.8:
            print("\n✓ GOOD: Most queries are fast enough")
        elif passed >= total * 0.5:
            print("\n⚠️ NEEDS IMPROVEMENT: Several slow queries detected")
        else:
            print("\n❌ CRITICAL: Database needs optimization!")
            print("\n   → Run: python add_indexes.py")
        
        print("\n" + "="*70)
        
    finally:
        db.close()

if __name__ == "__main__":
    try:
        print("\nInitializing database...")
        init_db()
        
        print("\nStarting benchmark...")
        run_benchmarks()
        
    except Exception as e:
        print(f"\n❌ Error running benchmarks: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
