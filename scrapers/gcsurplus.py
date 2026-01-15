"""
GCSurplus scraper - scrapes Canadian government surplus auctions.
Moved from app/scraper.py for better organization.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Optional
from datetime import datetime

from scrapers.base import BaseScraper
from config import settings


class GCSurplusScraper(BaseScraper):
    """Scraper for GCSurplus.ca auction listings"""
    
    def __init__(self):
        super().__init__()
        self.base_url = settings.base_url
        self.listing_url = settings.listing_url
        self.bid_api_url = settings.bid_api_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_source_name(self) -> str:
        return 'gcsurplus'
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all auction items from GCSurplus"""
        html = self.fetch_listing_page()
        if not html:
            return []
        
        items = self.parse_listing_page(html)
        
        # Standardize and validate all items
        validated_items = []
        for item in items:
            if self.validate_item(item):
                validated_items.append(self.standardize_item(item))
        
        self.logger.info(f"Successfully scraped {len(validated_items)} items from GCSurplus")
        return validated_items
    
    def scrape_single(self, lot_number: str) -> Optional[Dict]:
        """Scrape a single item by lot number"""
        # For now, scrape all and filter (can be optimized later)
        all_items = self.scrape_all()
        for item in all_items:
            if item.get('lot_number') == lot_number:
                return item
        return None
    
    def fetch_listing_page(self) -> Optional[str]:
        """Fetch the main listing page"""
        try:
            response = self.session.get(
                self.listing_url,
                timeout=settings.request_timeout
            )
            response.raise_for_status()
            self.logger.info(f"Successfully fetched listing page")
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching listing page: {e}")
            return None
    
    def parse_listing_page(self, html: str) -> List[Dict]:
        """Parse the listing page to extract auction items"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        try:
            # Debug: Save HTML to file for inspection
            with open('debug_gcsurplus.html', 'w', encoding='utf-8') as f:
                f.write(html)
            self.logger.info("Saved HTML to debug_gcsurplus.html for inspection")
            
            # Find the DataTable with auction items
            table = soup.find('table', {'id': 'displaySales'})
            if not table:
                # Try finding any table
                all_tables = soup.find_all('table')
                self.logger.warning(f"Could not find auction table with id='displaySales'. Found {len(all_tables)} tables total")
                
                # Try to find table by class or other attributes
                table = soup.find('table', class_=re.compile('dataTable|table'))
                if not table and all_tables:
                    table = all_tables[0]
                    self.logger.info("Using first table found")
                
                if not table:
                    return items
            
            tbody = table.find('tbody')
            if not tbody:
                # Try without tbody - some tables don't have it
                self.logger.warning("Could not find table body, trying direct rows")
                rows = table.find_all('tr')
            else:
                rows = tbody.find_all('tr')
            
            self.logger.info(f"Found {len(rows)} auction rows")
            
            if len(rows) == 0:
                self.logger.warning("No rows found in table - website structure may have changed")
                self.logger.info(f"Table HTML: {str(table)[:500]}")  # First 500 chars
            
            for row in rows:
                try:
                    item = self.parse_row(row)
                    if item:
                        items.append(item)
                except Exception as e:
                    self.logger.error(f"Error parsing row: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error parsing listing page: {e}")
        
        return items
    
    def parse_row(self, row) -> Optional[Dict]:
        """Parse a single table row to extract item data"""
        try:
            cells = row.find_all('td')
            if len(cells) < 4:
                return None
            
            # Extract lot number from link
            link = cells[0].find('a')
            if not link:
                return None
            
            href = link.get('href', '')
            lot_match = re.search(r'lcn=(\d+)', href)
            sale_match = re.search(r'scn=(\d+)', href)
            
            if not lot_match:
                return None
            
            lot_number = lot_match.group(1)
            sale_number = sale_match.group(1) if sale_match else None
            
            # Extract title
            title = link.get_text(strip=True)
            
            # Extract location (usually in second or third cell)
            location = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            
            # Parse location into city and province
            location_parts = location.split(',')
            location_city = location_parts[0].strip() if len(location_parts) > 0 else ""
            location_province = location_parts[1].strip() if len(location_parts) > 1 else ""
            
            # Extract closing date
            closing_date_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            closing_date = self.parse_date(closing_date_text)
            
            # Extract current bid
            bid_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            current_bid = self.parse_currency(bid_text)
            
            # Build item URL
            item_url = f"{self.base_url}{href}" if href and not href.startswith('http') else href
            
            item = {
                'lot_number': lot_number,
                'sale_number': sale_number,
                'title': title,
                'city': location_city,
                'region': location_province,
                'country': 'Canada',
                'closing_date': closing_date,
                'current_bid': current_bid,
                'currency': 'CAD',
                'item_url': item_url,
                'source': 'gcsurplus',
                'status': 'active',
                'is_available': True
            }
            
            # Try to fetch additional details (images, description, etc.)
            # This can be done asynchronously later for performance
            # detailed_item = self.fetch_item_details(lot_number, sale_number)
            # if detailed_item:
            #     item.update(detailed_item)
            
            return item
            
        except Exception as e:
            self.logger.error(f"Error parsing row: {e}")
            return None
    
    def parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date string to datetime object in UTC"""
        try:
            from datetime import timedelta
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                try:
                    dt = datetime.strptime(date_text, fmt)
                    # GCSurplus auctions are in Eastern Time
                    # For date-only formats, assume end of day (23:59:59 ET)
                    if fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                        dt = dt.replace(hour=23, minute=59, second=59)
                    # Convert from Eastern Time to UTC (add 5 hours for EST, 4 for EDT)
                    # For simplicity, use EST offset of +5 hours
                    dt = dt + timedelta(hours=5)
                    return dt
                except ValueError:
                    continue
            return None
        except:
            return None
    
    def parse_currency(self, currency_text: str) -> float:
        """Parse currency string to float"""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.]', '', currency_text)
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def fetch_item_details(self, lot_number: str, sale_number: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch detailed information for a specific item.
        This can include images, full description, etc.
        """
        # TODO: Implement detailed item fetching
        # This would make a separate request to get full item details
        return None
