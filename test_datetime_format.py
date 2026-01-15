"""
Test to verify datetime formatting for API responses
"""

from datetime import datetime
import pytz

# Test 1: Naive datetime (how we store in DB)
naive_dt = datetime(2026, 1, 13, 20, 4, 0)  # 8:04 PM UTC
print("Test 1: Naive datetime (stored in DB)")
print(f"  Value: {naive_dt}")
print(f"  isoformat(): {naive_dt.isoformat()}")
print(f"  Expected: 2026-01-13T20:04:00Z (with Z)")
print()

# Test 2: Add 'Z' manually
print("Test 2: Append Z for UTC")
print(f"  isoformat() + 'Z': {naive_dt.isoformat()}Z")
print()

# Test 3: What JavaScript sees
print("Test 3: JavaScript Date parsing")
print(f"  Without Z: new Date('{naive_dt.isoformat()}')")
print(f"    -> JavaScript treats this as LOCAL time! ❌")
print(f"  With Z:    new Date('{naive_dt.isoformat()}Z')")
print(f"    -> JavaScript treats this as UTC time! ✅")
print()

# Test 4: Example conversion
print("Test 4: Example - Auction closes at 2:04 PM CT")
print("  In CT (Central Time): 2:04 PM")
ct_tz = pytz.timezone('US/Central')
ct_dt = ct_tz.localize(datetime(2026, 1, 13, 14, 4, 0))
utc_dt = ct_dt.astimezone(pytz.UTC).replace(tzinfo=None)
print(f"  In UTC (stored in DB): {utc_dt}")
print(f"  API returns: {utc_dt.isoformat()}")
print(f"  Should return: {utc_dt.isoformat()}Z")
print()
print("  If user is in New York (ET):")
print(f"    Without Z: Shows as {utc_dt.strftime('%I:%M %p')} ET (wrong - 8:04 PM)")
print(f"    With Z:    Shows as 3:04 PM ET (correct!)")
