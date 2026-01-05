# Treasury.gov Real Estate Auction Scraper

## Overview

This scraper collects upcoming real estate auction data from the US Treasury Department's seized property auction website. These are **upcoming auctions** that have not yet started bidding.

## Source

- **Website**: https://www.treasury.gov/auctions/treasury/rp/realprop.shtml
- **Type**: Real Estate (seized properties)
- **Status**: Upcoming auctions
- **Agency**: US Department of Treasury

## Features

### Data Collection

The scraper extracts:

#### Basic Information
- **Property Address**: Full street address
- **City & State**: Location details
- **Title**: Property description
- **Sale Number**: Unique auction identifier
- **Asset Type**: Always `real-estate`

#### Auction Details
- **Auction Date & Time**: When the auction will occur
- **Starting Bid**: Minimum bid amount
- **Deposit**: Required deposit amount
- **Inspection Dates**: When property can be viewed

#### Property Details (from detail pages)
- **Living Space**: Square footage
- **Site Area**: Lot size
- **Year Built**: Construction year
- **County**: County location
- **County Taxes**: Annual property tax
- **Zoning**: Property zoning classification
- **Parcel Number**: Tax parcel ID
- **Utilities**: Available utilities (electric, gas, water, sewer)

#### Media
- **Images**: Property photos
- **Floor Plans**: Link to floor plan (when available)
- **Detail Page URL**: Link to full auction details

## How It Works

### 1. List Page Scraping
The scraper first visits the main listing page and extracts:
- Property addresses and locations
- Auction dates
- Starting bids
- Sale numbers
- Links to detail pages
- Thumbnail images

### 2. Detail Page Scraping
For each property, the scraper visits the detail page to collect:
- Full property description
- Detailed specifications (sq ft, lot size, etc.)
- Additional images
- County information
- Zoning details
- Inspection information

### 3. Data Storage
All data is stored in the database with:
- `source`: `treasury`
- `auction_type`: `upcoming`
- `status`: `upcoming`
- `asset_type`: `real-estate`

## Database Schema

The Treasury scraper uses the standard `AuctionItem` model with the existing `status` field:

```python
{
    "lot_number": "treasury-{sale_number}",  # Unique identifier
    "sale_number": "26-66-809",              # Treasury sale number
    "source": "treasury",
    "status": "upcoming",                     # Uses existing status field!
    "asset_type": "real-estate",
    "title": "Property address",
    "description": "Full property description",
    "location_address": "Full street address",
    "location_city": "City name",
    "location_state": "State code (e.g., NM)",
    "minimum_bid": 75000.00,
    "closing_date": "2026-01-30 13:00:00",  # Auction datetime
    "agency": "US Department of Treasury",
    "item_url": "Detail page URL",
    "image_urls": ["url1", "url2", ...],
    "extra_data": {
        "deposit": "$20,000",
        "living_space": "1,956 ± sq. ft.",
        "site_area": "10,800 ± sq. ft.",
        "year_built": "1996",
        "county": "Bernalillo",
        "county_taxes": "$2,713.00 ±",
        "zoning": "R-1C/Single Family",
        "parcel_number": "101105839024341438",
        "utilities": "Electric, Gas, Water, Sewer",
        "inspection_date": "Sunday, January 25, 11:00am - 3:00pm",
        "auction_time": "Friday, January 30, 2026 at 11-1pm MT"
    }
}
```

## API Endpoints

### Get All Treasury Auctions
```
GET /api/auctions/treasury
```

### Get All Upcoming Auctions (including Treasury)
```
GET /api/auctions/upcoming
```

### Trigger Treasury Scrape
```
POST /api/scrape/treasury
```

### Scrape All Sources (includes Treasury)
```
POST /api/scrape/all
```

## Usage

### 1. Test the Scraper
```bash
python test_treasury_scraper.py
```

### 2. Run Manual Scrape
```bash
curl -X POST http://localhost:8001/api/scrape/treasury
```

### 4. Get Results
```bash
curl http://localhost:8001/api/auctions/treasury
```

## Configuration

Add to `.env` or use defaults in `config.py`:

```env
treasury_base_url=https://www.treasury.gov/auctions/treasury/rp
treasury_listing_url=https://www.treasury.gov/auctions/treasury/rp/realprop.shtml
```

## Frontend Integration

### Upcoming Auctions Page

The frontend should display these auctions on an "Upcoming Auctions" page since they:
- Haven't started bidding yet
- Have future auction dates
- Are marked as `auction_type: "upcoming"`

### Display Fields

Recommended fields to display:
- Property image
- Property address
- City, State
- Starting bid
- Auction date & time
- Inspection dates
- Deposit amount
- Property details (sq ft, lot size, etc.)
- Link to detail page
- "View Details" button

### Filtering

Filter by:
- Location (city/state)
- Price range (starting bid)
- Auction date range
- Property type

## Important Notes

### "Currently Not Available"

If detail pages are not accessible, the scraper will:
- Still collect listing page data
- Mark unavailable fields as "Currently not available"
- Save what data is available
- Continue processing other items

### Upcoming vs Active

- **Upcoming** (status='upcoming'): Treasury auctions (not yet accepting bids)
- **Active** (status='active'): GCSurplus/GSA auctions (currently accepting bids)
- **Closed** (status='closed'): Completed auctions
- **Expired** (status='expired'): Expired auctions

The frontend should separate these using the `status` field.

### Auction Types

Treasury auctions are different from GCSurplus/GSA:
- **Treasury**: Sealed bid auctions on specific dates
- **GCSurplus/GSA**: Open bidding with closing dates

### Data Quality

The scraper handles:
- Missing detail pages
- Incomplete property information
- Date parsing variations
- Multiple image formats

## Error Handling

The scraper includes robust error handling:
- Continues if a detail page fails
- Logs all errors with context
- Doesn't crash the entire scrape
- Marks items as unavailable if needed

## Maintenance

### Update Frequency

Recommended scrape schedule:
- **Weekly**: Treasury auctions don't change frequently
- **Daily**: If you want to catch new listings quickly

### Monitoring

Check logs for:
- Number of items scraped
- Detail page access success rate
- Missing field warnings
- Error patterns

## Troubleshooting

### No Items Found

1. Check if the website structure changed
2. Verify the listing URL is correct
3. Check for network/firewall issues
4. Review logs for parsing errors

### Detail Pages Not Loading

1. Detail page URLs may be temporary
2. Some auctions may not have detail pages yet
3. Check the `item_url` in the database

### Missing Data

1. Some fields are optional and may not exist
2. Check `extra_data` for additional information
3. Detail page may not have loaded successfully

## Future Enhancements

Potential improvements:
- Email notifications for new auctions
- Price drop alerts
- Saved search functionality
- Property comparison features
- Bidding reminder system

## Support

For issues or questions:
1. Check logs: `logs/scraper.log`
2. Run test script: `python test_treasury_scraper.py`
3. Review error messages in console
4. Check database for partial data
