"""
U.S. Embassy Online Auction Scraper
Fetches auction data from https://online-auction.state.gov/en-US
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import re
import logging
import pytz
import pycountry

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

class StateDeptScraper(BaseScraper):
    """Scraper for U.S. Embassy Online Auctions"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://online-auction.state.gov"
        self.start_url = f"{self.base_url}/en-US"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_source_name(self) -> str:
        return 'state_dept'

    def scrape_all(self) -> List[Dict]:
        """Scrape all available auctions from the state.gov site"""
        try:
            self.logger.info(f"Fetching main page: {self.start_url}")
            response = self.session.get(self.start_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            auction_items = []
            
            # Find all auction blocks
            auction_blocks = soup.find_all('div', class_='auction-list')
            self.logger.info(f"Found {len(auction_blocks)} auction blocks on main page")
            
            for block in auction_blocks:
                try:
                    # Extract auction metadata from the block
                    metadata = self._parse_auction_block(block)
                    if not metadata or not metadata.get('guid'):
                        continue
                        
                    # Fetch details for the auction if it's active or preparing
                    # Note: "Preparing" auctions might not have lot details yet, but we can still save them
                    detail_url = f"{self.base_url}/en-US/Auction/Index/{metadata['guid']}"
                    metadata['item_url'] = detail_url
                    
                    if metadata['status'] == 'active':
                        lots = self._scrape_auction_details(detail_url, metadata)
                        auction_items.extend(lots)
                    else:
                        # For upcoming/preparing, we might not have lots, so we create a dummy "Auction info" item 
                        # or just skip. The user wants them saved. 
                        # Usually, these sites show lots even in Preparing phase if available.
                        lots = self._scrape_auction_details(detail_url, metadata)
                        if lots:
                            auction_items.extend(lots)
                        else:
                            # If no lots, create one entry representing the auction itself?
                            # Our model is based on "AuctionItem" (lots).
                            # Let's try to scrape details regardless.
                            pass
                            
                except Exception as e:
                    self.logger.error(f"Error parsing auction block: {e}")
                    continue
            
            self.logger.info(f"Total items scraped from State Dept: {len(auction_items)}")
            return auction_items
            
        except Exception as e:
            self.logger.error(f"Failed to scrape State Dept auctions: {e}")
            return []

    def _parse_auction_block(self, block) -> Optional[Dict]:
        """Extract auction GUID, location, status, and dates from a block on the listing page"""
        container = block.find('div', class_='label-postname-container')
        if not container:
            return None
            
        # Extract GUID from onclick (handles both onclick and onkeypress)
        onclick = container.get('onclick', '') or container.get('onkeypress', '')
        guid_match = re.search(r'/en-US/Auction/Index/([a-zA-Z0-9-]+)', onclick, re.IGNORECASE)
        if not guid_match:
            self.logger.debug(f"Could not extract GUID from onclick: {onclick[:100]}")
            return None
        guid = guid_match.group(1)
        
        # Location - Look for a div containing city/country info
        location_div = container.find('div', style=re.compile(r'text-align:\s*center'))
        if not location_div:
            # Fallback: try to find any div with location-like text near the container
            location_div = block.find('div', string=re.compile(r',\s*[A-Z]{2}'))
        location_text = location_div.get_text(strip=True) if location_div else "Unknown"
        
        # Status
        status_label = block.find('div', class_='status label')
        status_text = status_label.get_text(strip=True).lower() if status_label else "unknown"
        
        # Map status
        mapped_status = 'active'
        if 'preparing' in status_text:
            mapped_status = 'upcoming'
        elif 'closed' in status_text:
            mapped_status = 'closed'
            
        # Dates - Look for span with localdatetime attribute
        date_span = block.find('span', attrs={'localdatetime': True})
        date_val = None
        if date_span:
            # The date text is directly in this span
            raw_date = date_span.get_text(strip=True)  # Format: 2026-01-20 11:00:00Z
            try:
                # Parse the datetime string
                if raw_date and raw_date.endswith('Z'):
                    clean_date = raw_date.replace('Z', '+00:00')
                    date_val = datetime.fromisoformat(clean_date)
                elif raw_date:
                    # Try parsing without timezone
                    try:
                        date_val = datetime.strptime(raw_date, '%Y-%m-%d %H:%M:%S')
                        # Assume UTC
                        date_val = date_val.replace(tzinfo=pytz.UTC)
                    except ValueError:
                        pass
            except Exception as e:
                self.logger.debug(f"Could not parse date: {raw_date}, error: {e}")

        return {
            'guid': guid,
            'location_raw': location_text,
            'status': mapped_status,
            'date': date_val
        }

    def _scrape_auction_details(self, url: str, metadata: Dict) -> List[Dict]:
        """Fetch detail page and parse individual lots from all pages"""
        all_lots = []
        page_num = 1
        
        # Initialize location variables that will be set on first page
        currency = "USD"
        city = metadata['location_raw']
        country = ""
        country_code = ""
        
        while True:
            try:
                # Construct URL for current page
                if page_num == 1:
                    page_url = url
                else:
                    page_url = f"{url}/Page/{page_num}"
                
                self.logger.info(f"Fetching page {page_num}: {page_url}")
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Parse metadata on first page only
                if page_num == 1:
                    # Find currency
                    currency_msg = soup.find(string=re.compile(r'Prices in', re.I))
                    if currency_msg:
                        # Extracts "USD" from "Prices in USD ($)"
                        cur_match = re.search(r'in\s+([A-Z]{3})', currency_msg)
                        if cur_match:
                            currency = cur_match.group(1)
                    
                    # Parse "City, CountryCode" format from location_raw
                    if ',' in metadata['location_raw']:
                        parts = metadata['location_raw'].split(',')
                        city = parts[0].strip()
                        country_code = parts[-1].strip()
                        
                        # Convert ISO 2-letter code to full country name
                        try:
                            country_obj = pycountry.countries.get(alpha_2=country_code)
                            if country_obj:
                                country = country_obj.name
                            else:
                                # Fallback to code if not found
                                country = country_code
                        except Exception as e:
                            self.logger.debug(f"Could not resolve country code '{country_code}': {e}")
                            country = country_code

                # Find all lot containers (each auction item) on this page
                lot_containers = soup.find_all('div', class_='oa-lot-container')
                self.logger.info(f"Found {len(lot_containers)} lots on page {page_num}")
                
                # No lots on this page, we've reached the end
                if not lot_containers:
                    self.logger.info(f"No more lots found, stopping at page {page_num}")
                    break
                
                for container in lot_containers:
                    try:
                        # Find the oa-lot-details div within the container
                        lot_details = container.find('div', class_='oa-lot-details')
                        if not lot_details:
                            continue
                        
                        # Title - in 'name-of-the-item' div
                        title_div = lot_details.find('div', class_='name-of-the-item')
                        if not title_div:
                            self.logger.debug("No title found, skipping lot")
                            continue
                        
                        title = title_div.get_text(strip=True)
                        
                        # Lot number - in 'oa-lot-number' div
                        lot_num = "unknown"
                        lot_num_div = lot_details.find('div', class_='oa-lot-number')
                        if lot_num_div:
                            # The lot number is in a nested div with class 'form-control'
                            lot_num_val = lot_num_div.find('div', class_='form-control')
                            if lot_num_val:
                                lot_num = lot_num_val.get_text(strip=True)
                        
                        # More robust lot_number for DB uniqueness
                        db_lot_number = f"state-{metadata['guid']}-lot{lot_num}"
                        
                        # Status of this specific lot
                        lot_status = metadata['status']
                        status_indicator = lot_details.find('div', class_='oa-generic-status-indicator')
                        if status_indicator:
                            lot_status_text = status_indicator.get_text(strip=True).lower()
                            if 'active' in lot_status_text:
                                lot_status = 'active'
                            elif 'preparing' in lot_status_text:
                                lot_status = 'upcoming'
                            elif 'closed' in lot_status_text:
                                lot_status = 'closed'

                        # Current Price - Look for label "Current price" or "Current Bid"
                        current_bid = 0.0
                        price_label = lot_details.find(string=re.compile(r'Current (price|Bid)', re.I))
                        if price_label:
                            # Find the parent form-group, then find the div with the price
                            form_group = price_label.find_parent('div', class_='form-group')
                            if form_group:
                                price_div = form_group.find('div', class_='form-control')
                                if price_div:
                                    price_text = price_div.get_text(strip=True).replace(',', '')
                                    price_match = re.search(r'(\d+\.?\d*)', price_text)
                                    if price_match:
                                        current_bid = float(price_match.group(1))

                        # Description
                        description = ""
                        desc_label = lot_details.find(string=re.compile(r'Description', re.I))
                        if desc_label:
                            form_group = desc_label.find_parent('div', class_='form-group')
                            if form_group:
                                desc_div = form_group.find('div', class_='form-control')
                                if desc_div:
                                    description = desc_div.get_text(strip=True)[:500]  # Limit to 500 chars

                        # Image URL - Look for images in the container
                        image_urls = []
                        # Look in the whole container, not just lot_details
                        img_tags = container.find_all('img', class_='lot-image-thumb')
                        for img in img_tags:
                            src = img.get('src')
                            if src:
                                if src.startswith('/'):
                                    src = self.base_url + src
                                image_urls.append(src)

                        item = {
                            'lot_number': db_lot_number,
                            'sale_number': metadata['guid'][:8].upper(),
                            'title': title,
                            'source': self.get_source_name(),
                            'current_bid': current_bid,
                            'status': lot_status,
                            'city': city,
                            'country': country,
                            'currency': currency,
                            'closing_date': metadata['date'],
                            'image_urls': image_urls,
                            'item_url': page_url,  # Use page URL so it points to the correct page
                            'description': description or f"Auction Location: {metadata['location_raw']}",
                            'address_raw': metadata['location_raw'],
                            'extra_data': {
                                'original_location': metadata['location_raw'],
                                'guid': metadata['guid'],
                                'lot_number': lot_num,
                                'page': page_num,
                                'country_code': country_code if 'country_code' in locals() else ''
                            }
                        }
                        
                        if self.validate_item(item):
                            all_lots.append(self.standardize_item(item))
                        else:
                            self.logger.warning(f"Failed validation for lot: {title[:50]}")
                            
                    except Exception as e:
                        self.logger.error(f"Error parsing lot on page {page_num}: {e}")
                        continue
                
                # Check for next page - look for pagination
                pagination = soup.find('ul', class_='pagination')
                has_next_page = False
                if pagination:
                    next_link = pagination.find('li', class_='PagedList-skipToNext')
                    if next_link and 'disabled' not in next_link.get('class', []):
                        has_next_page = True
                
                if not has_next_page:
                    self.logger.info(f"No more pages found after page {page_num}")
                    break
                
                # Move to next page
                page_num += 1
                
            except Exception as e:
                self.logger.error(f"Error scraping page {page_num} for {url}: {e}")
                break
        
        self.logger.info(f"Total lots scraped from all pages: {len(all_lots)}")
        return all_lots

    def scrape_single(self, item_id: str) -> Optional[Dict]:
        # Implementation for single item if needed
        return None
