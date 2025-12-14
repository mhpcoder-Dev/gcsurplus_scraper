import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import re
from app.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


class GCSurplusScraper:
    """Scraper for GCSurplus.ca auction listings"""
    
    def __init__(self):
        self.base_url = settings.base_url
        self.listing_url = settings.listing_url
        self.bid_api_url = settings.bid_api_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_listing_page(self) -> Optional[str]:
        """Fetch the main listing page"""
        try:
            response = self.session.get(
                self.listing_url,
                timeout=settings.request_timeout
            )
            response.raise_for_status()
            logger.info(f"Successfully fetched listing page")
            return response.text
        except Exception as e:
            logger.error(f"Error fetching listing page: {e}")
            return None
    
    def parse_listing_page(self, html: str) -> List[Dict]:
        """Parse the listing page to extract auction items"""
        soup = BeautifulSoup(html, 'lxml')
        items = []
        
        try:
            # Find the DataTable with auction items
            table = soup.find('table', {'id': 'displaySales'})
            if not table:
                logger.warning("Could not find auction table")
                return items
            
            tbody = table.find('tbody')
            if not tbody:
                logger.warning("Could not find table body")
                return items
            
            rows = tbody.find_all('tr')
            logger.info(f"Found {len(rows)} auction rows")
            
            for row in rows:
                try:
                    item = self.parse_row(row)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.error(f"Error parsing row: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing listing page: {e}")
        
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
            
            # Extract closing date (usually in one of the cells)
            closing_date_text = ""
            for cell in cells:
                text = cell.get_text(strip=True)
                if any(month in text.lower() for month in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
                    closing_date_text = text
                    break
            
            # Parse location
            location_parts = location.split(',') if location else []
            city = location_parts[0].strip() if location_parts else ""
            province = location_parts[1].strip() if len(location_parts) > 1 else ""
            
            item = {
                'lot_number': lot_number,
                'sale_number': sale_number,
                'title': title,
                'location_city': city,
                'location_province': province,
                'closing_date_text': closing_date_text,
                'detail_url': f"{self.base_url}/{href}" if not href.startswith('http') else href,
                'is_available': True
            }
            
            return item
            
        except Exception as e:
            logger.error(f"Error parsing row: {e}")
            return None
    
    def fetch_item_details(self, lot_number: str) -> Optional[Dict]:
        """Fetch detailed information for a specific item"""
        try:
            # Construct detail page URL
            detail_url = f"{self.base_url}/mn-eng.cfm?snc=wfsav&sc=enc-bid&vndsld=0&lci=&lcn={lot_number}&str=1&sf=aff-post&so=DESC"
            
            response = self.session.get(detail_url, timeout=settings.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            details = {}
            
            # Extract current bid
            current_bid_elem = soup.find('span', {'id': 'currentBid'})
            if current_bid_elem:
                bid_text = current_bid_elem.get_text(strip=True)
                details['current_bid'] = self.parse_currency(bid_text)
            
            # Extract minimum bid
            min_bid_elem = soup.find('span', {'id': 'openBidMin'})
            if min_bid_elem:
                min_bid_text = min_bid_elem.get_text(strip=True)
                details['next_minimum_bid'] = self.parse_currency(min_bid_text)
            
            # Extract bid increment
            incr_elem = soup.find('span', {'id': 'openBidIncr'})
            if incr_elem:
                incr_text = incr_elem.get_text(strip=True)
                details['bid_increment'] = self.parse_currency(incr_text)
            
            # Extract time remaining
            time_elem = soup.find('span', {'id': 'timeRemaining'})
            if time_elem:
                details['time_remaining'] = time_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = soup.find('span', {'id': 'itemCmntId'})
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)
            
            # Extract quantity
            qty_pattern = re.search(r'Quantity:\s*(\d+)', response.text)
            if qty_pattern:
                details['quantity'] = int(qty_pattern.group(1))
            
            # Extract images
            images = []
            for img in soup.find_all('img', {'class': 'newViewer'}):
                img_src = img.get('src', '')
                if img_src and not img_src.startswith('data:'):
                    full_url = f"{self.base_url}/{img_src}" if not img_src.startswith('http') else img_src
                    images.append(full_url)
            details['image_urls'] = json.dumps(images)
            
            # Extract contact info
            contact_pattern = re.search(r'Contact.*?:\s*</dt>\s*<dd>(.*?)</dd>', response.text, re.DOTALL)
            if contact_pattern:
                contact_text = BeautifulSoup(contact_pattern.group(1), 'lxml').get_text(strip=True)
                details['contact_name'] = contact_text.split('\n')[0] if contact_text else None
            
            # Extract sale/lot number
            sale_lot_pattern = re.search(r'Sale / Lot\s*:\s*</dt>\s*<dd[^>]*>(.*?)</dd>', response.text, re.DOTALL)
            if sale_lot_pattern:
                sale_lot_text = BeautifulSoup(sale_lot_pattern.group(1), 'lxml').get_text(strip=True)
                details['sale_lot'] = sale_lot_text
            
            return details
            
        except Exception as e:
            logger.error(f"Error fetching details for lot {lot_number}: {e}")
            return None
    
    def check_bid_status(self, lot_number: str) -> Optional[Dict]:
        """Check bid status using the API endpoint"""
        try:
            url = f"{self.bid_api_url}?method=getLastFastBid&delay=false&removeMax=false&lotNo={lot_number}&lang=eng"
            
            response = self.session.get(url, timeout=settings.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if item exists and is still available
            if data.get('RETURN_CD') == 200:
                # Safely convert to float, handling empty strings
                bid_amt = data.get('BID_AMT', 0)
                next_bid_amt = data.get('NEXT_BID_AMT', 0)
                bid_increment = data.get('BID_INCREMENT', 0)
                
                return {
                    'exists': True,
                    'current_bid': float(bid_amt) if bid_amt != '' else 0.0,
                    'next_minimum_bid': float(next_bid_amt) if next_bid_amt != '' else 0.0,  # Match database field name
                    'bid_increment': float(bid_increment) if bid_increment != '' else 0.0,
                    'time_remaining': data.get('REMAINING', '')  # Match database field name
                }
            else:
                return {'exists': False}
                
        except Exception as e:
            logger.error(f"Error checking bid status for lot {lot_number}: {e}")
            return None
    
    @staticmethod
    def parse_currency(text: str) -> float:
        """Parse currency string to float"""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.]', '', text)
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all auction listings"""
        logger.info("Starting full scrape...")
        
        # Fetch listing page
        html = self.fetch_listing_page()
        if not html:
            logger.error("Failed to fetch listing page")
            return []
        
        # Parse items
        items = self.parse_listing_page(html)
        logger.info(f"Parsed {len(items)} items from listing page")
        
        # Fetch details for each item
        enriched_items = []
        for item in items[:50]:  # Limit to 50 items to avoid overwhelming the server
            try:
                lot_number = item['lot_number']
                logger.info(f"Fetching details for lot {lot_number}")
                
                # Get detailed info
                details = self.fetch_item_details(lot_number)
                if details:
                    item.update(details)
                
                # Check bid status
                bid_status = self.check_bid_status(lot_number)
                if bid_status and bid_status.get('exists'):
                    # Remove 'exists' field as it's not in the database model
                    bid_status.pop('exists', None)
                    item.update(bid_status)
                
                enriched_items.append(item)
                
            except Exception as e:
                logger.error(f"Error enriching item {item.get('lot_number')}: {e}")
                enriched_items.append(item)  # Add anyway with basic info
        
        logger.info(f"Completed scrape with {len(enriched_items)} items")
        return enriched_items
