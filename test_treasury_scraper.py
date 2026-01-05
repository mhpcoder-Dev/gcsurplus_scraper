"""
Test script for Treasury.gov scraper.
Tests scraping functionality without writing to database.
"""

import logging
from scrapers.treasury import TreasuryScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_treasury_scraper():
    """Test the Treasury scraper"""
    logger.info("=" * 80)
    logger.info("Testing Treasury.gov Scraper")
    logger.info("=" * 80)
    
    # Initialize scraper
    scraper = TreasuryScraper()
    
    # Test scraping
    logger.info("\n1. Testing scrape_all()...")
    items = scraper.scrape_all()
    
    logger.info(f"\n✓ Successfully scraped {len(items)} items from Treasury.gov")
    
    # Display sample items
    if items:
        logger.info("\n" + "=" * 80)
        logger.info("Sample Auction Items:")
        logger.info("=" * 80)
        
        for i, item in enumerate(items[:3], 1):  # Show first 3 items
            logger.info(f"\nItem {i}:")
            logger.info(f"  Lot Number: {item.get('lot_number')}")
            logger.info(f"  Sale Number: {item.get('sale_number')}")
            logger.info(f"  Title: {item.get('title')}")
            logger.info(f"  Location: {item.get('location_city')}, {item.get('location_state')}")
            logger.info(f"  Address: {item.get('location_address', 'N/A')}")
            logger.info(f"  Status: {item.get('status')} (upcoming auction)")
            logger.info(f"  Asset Type: {item.get('asset_type')}")
            logger.info(f"  Starting Bid: ${item.get('minimum_bid', 0):,.2f}" if item.get('minimum_bid') else "  Starting Bid: Not available")
            logger.info(f"  Auction Date: {item.get('closing_date')}")
            logger.info(f"  Item URL: {item.get('item_url', 'N/A')}")
            logger.info(f"  Images: {len(item.get('image_urls', []))} image(s)")
            logger.info(f"  Description: {item.get('description', 'N/A')[:150]}...")
            
            # Show extra data
            extra_data = item.get('extra_data', {})
            if extra_data:
                logger.info(f"  Extra Data:")
                for key, value in extra_data.items():
                    logger.info(f"    - {key}: {value}")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"Total items scraped: {len(items)}")
        logger.info("=" * 80)
        
        # Statistics
        logger.info("\nStatistics:")
        with_details = sum(1 for item in items if item.get('item_url'))
        with_bids = sum(1 for item in items if item.get('minimum_bid'))
        with_dates = sum(1 for item in items if item.get('closing_date'))
        
        logger.info(f"  Items with detail URLs: {with_details}/{len(items)}")
        logger.info(f"  Items with starting bids: {with_bids}/{len(items)}")
        logger.info(f"  Items with auction dates: {with_dates}/{len(items)}")
    else:
        logger.warning("\n⚠ No items were scraped. This could mean:")
        logger.warning("  1. The listing page structure has changed")
        logger.warning("  2. There are no active auctions on the site")
        logger.warning("  3. The website is blocking the scraper")
    
    return items


if __name__ == "__main__":
    try:
        items = test_treasury_scraper()
        
        if items:
            logger.info("\n✓ Test completed successfully!")
            logger.info(f"✓ Scraper is working correctly and found {len(items)} auctions")
        else:
            logger.warning("\n⚠ Test completed but no items were found")
            
    except Exception as e:
        logger.error(f"\n✗ Test failed with error: {e}", exc_info=True)
