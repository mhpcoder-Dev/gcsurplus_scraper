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
            
        # Extract GUID from onclick
        onclick = container.get('onclick', '')
        guid_match = re.search(r'/en-US/Auction/Index/([a-z0-9-]+)', onclick)
        if not guid_match:
            return None
        guid = guid_match.group(1)
        
        # Location
        location_div = block.find('div', style=re.compile(r'text-align:\s*center'))
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
            
        # Dates
        date_span = block.find('span', localdatetime=True)
        date_val = None
        if date_span:
            raw_date = date_span.get('localdatetime') # Format: 2026-01-14 10:00:00Z
            try:
                # Replace 'Z' with '+0000' for parsing or just use fromisoformat
                clean_date = raw_date.replace('Z', '+00:00')
                date_val = datetime.fromisoformat(clean_date)
            except:
                pass

        return {
            'guid': guid,
            'location_raw': location_text,
            'status': mapped_status,
            'date': date_val
        }

    def _scrape_auction_details(self, url: str, metadata: Dict) -> List[Dict]:
        """Fetch detail page and parse individual lots"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find currency
            currency = "USD"
            currency_msg = soup.find(string=re.compile(r'Prices in', re.I))
            if currency_msg:
                # Extracts "USD" from "Prices in USD ($)"
                cur_match = re.search(r'in\s+([A-Z]{3})', currency_msg)
                if cur_match:
                    currency = cur_match.group(1)
            
            # Location parsing
            city = metadata['location_raw']
            country = ""
            if ',' in city:
                parts = city.split(',')
                city = parts[0].strip()
                country = parts[1].strip()

            lots = []
            lot_containers = soup.find_all('div', class_='oa-lot-details')
            
            for container in lot_containers:
                try:
                    title_div = container.find('div', class_='name-of-the-item')
                    if not title_div:
                        continue
                    
                    full_title = title_div.get_text(strip=True)
                    # "Lot#1: Title"
                    lot_num = "unknown"
                    title = full_title
                    if ':' in full_title:
                        lot_num_part, title = full_title.split(':', 1)
                        lot_num = lot_num_part.replace('Lot#', '').strip()
                        title = title.strip()
                    
                    # More robust lot_number for DB uniqueness
                    db_lot_number = f"state-{metadata['guid']}-{lot_num}"
                    
                    # Status of this specific lot
                    lot_status = metadata['status']
                    status_indicator = container.find('div', class_='oa-generic-status-indicator')
                    if status_indicator:
                        lot_status_text = status_indicator.get_text(strip=True).lower()
                        if 'active' in lot_status_text:
                            lot_status = 'active'
                        elif 'preparing' in lot_status_text:
                            lot_status = 'upcoming'
                        elif 'closed' in lot_status_text:
                            lot_status = 'closed'

                    # Current Bid
                    current_bid = 0.0
                    # Often bid is in a span or div near the bottom
                    # Look for "Current Bid" label
                    bid_label = container.find(string=re.compile(r'Current Bid', re.I))
                    if bid_label:
                        bid_val_node = bid_label.find_parent('div').find_next_sibling('div')
                        if bid_val_node:
                            bid_text = bid_val_node.get_text(strip=True).replace(',', '')
                            bid_match = re.search(r'(\d+\.?\d*)', bid_text)
                            if bid_match:
                                current_bid = float(bid_match.group(1))

                    # Image URL
                    image_urls = []
                    img_tag = container.find_all('img')
                    for img in img_tag:
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
                        'item_url': url,
                        'description': f"Auction Location: {metadata['location_raw']}",
                        'address_raw': metadata['location_raw'],
                        'extra_data': {
                            'original_location': metadata['location_raw'],
                            'guid': metadata['guid']
                        }
                    }
                    
                    if self.validate_item(item):
                        lots.append(self.standardize_item(item))
                        
                except Exception as e:
                    self.logger.error(f"Error parsing lot in {url}: {e}")
                    continue
            
            return lots

        except Exception as e:
            self.logger.error(f"Error scraping details for {url}: {e}")
            return []

    def scrape_single(self, item_id: str) -> Optional[Dict]:
        # Implementation for single item if needed
        return None
