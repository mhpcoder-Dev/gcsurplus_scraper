#!/usr/bin/env python
"""
Quick test script to verify DTO and multi-environment implementation.
Run this after starting the FastAPI server.
"""

import requests
import json
from pprint import pprint

BASE_URL = "http://localhost:8000"

def test_environment():
    """Test environment configuration"""
    print("=" * 60)
    print("Testing Environment Configuration")
    print("=" * 60)
    
    # Test root endpoint
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        print("✓ Server is running")
        data = response.json()
        print(f"  Environment: {data.get('environment', 'N/A')}")
        print(f"  Version: {data.get('version', 'N/A')}")
    else:
        print("✗ Server not responding")
        return False
    
    print()
    return True

def test_auction_list_dto():
    """Test auction list endpoint returns DTO structure"""
    print("=" * 60)
    print("Testing Auction List DTO")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/auctions?limit=2")
    
    if response.status_code == 200:
        data = response.json()
        
        # Check DTO structure
        print("✓ Response received")
        
        # Check for new DTO structure
        if "pagination" in data:
            print("✓ DTO structure detected (pagination key exists)")
            print(f"  Total items: {data['pagination']['total']}")
            print(f"  Page: {data['pagination']['page']}/{data['pagination']['total_pages']}")
        else:
            print("✗ Old structure detected (no pagination key)")
            return False
        
        # Check items structure
        if data.get("items"):
            item = data["items"][0]
            print("✓ Items present")
            
            # Check nested objects
            if "location" in item and isinstance(item["location"], dict):
                print("✓ Location is nested object")
                print(f"  City: {item['location'].get('city', 'N/A')}")
            else:
                print("✗ Location not nested")
            
            if "bidding" in item and isinstance(item["bidding"], dict):
                print("✓ Bidding is nested object")
                print(f"  Current bid: {item['bidding'].get('current_bid', 'N/A')}")
            else:
                print("✗ Bidding not nested")
            
            # Check image_urls is string (first image only)
            if isinstance(item.get("image_urls"), (str, type(None))):
                print("✓ image_urls is string (first image only)")
            else:
                print("  Note: image_urls is array (this is ok for detail view)")
        
        print("\nSample DTO structure:")
        pprint(data, depth=3)
        
    else:
        print(f"✗ Request failed: {response.status_code}")
        return False
    
    print()
    return True

def test_auction_detail_dto():
    """Test single auction endpoint returns detail DTO"""
    print("=" * 60)
    print("Testing Auction Detail DTO")
    print("=" * 60)
    
    # First get a lot number
    response = requests.get(f"{BASE_URL}/api/auctions?limit=1")
    if response.status_code != 200:
        print("✗ Could not fetch auctions list")
        return False
    
    data = response.json()
    if not data.get("items"):
        print("✗ No auctions available")
        return False
    
    lot_number = data["items"][0]["lot_number"]
    source = data["items"][0]["source"]
    
    # Test detail endpoint
    response = requests.get(f"{BASE_URL}/api/auctions/{lot_number}?source={source}")
    
    if response.status_code == 200:
        item = response.json()
        
        print("✓ Detail response received")
        print(f"  Lot number: {lot_number}")
        print(f"  Title: {item.get('title', 'N/A')[:50]}...")
        
        # Check for detail-specific fields
        if "description" in item:
            print("✓ Description present")
        
        if "extra_data" in item and isinstance(item["extra_data"], dict):
            print("✓ extra_data is parsed object")
        
        if "image_urls" in item and isinstance(item["image_urls"], list):
            print(f"✓ image_urls is array ({len(item['image_urls'])} images)")
        
        # Check nested objects
        if isinstance(item.get("location"), dict):
            print("✓ Location is nested object")
        
        if isinstance(item.get("bidding"), dict):
            print("✓ Bidding is nested object")
        
        print("\nSample Detail DTO:")
        # Print without description to keep it short
        sample = {k: v for k, v in item.items() if k != "description"}
        pprint(sample, depth=3)
        
    else:
        print(f"✗ Request failed: {response.status_code}")
        return False
    
    print()
    return True

def test_api_docs():
    """Test API documentation is accessible"""
    print("=" * 60)
    print("Testing API Documentation")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/docs")
    if response.status_code == 200:
        print("✓ API docs accessible at /docs")
        print("  Open http://localhost:8000/docs to see DTO schemas")
    else:
        print("✗ API docs not accessible")
        return False
    
    print()
    return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DTO & Multi-Environment Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        test_environment,
        test_auction_list_dto,
        test_auction_detail_dto,
        test_api_docs
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print(f"✗ {total - passed} test(s) failed")
    
    print("\nNext steps:")
    print("1. Check server logs for environment loading")
    print("2. Update frontend to use new DTO structure")
    print("3. Test with different ENVIRONMENT values")
    print("=" * 60 + "\n")
