"""
Treasury.gov scraper - scrapes US Treasury seized real property auctions.
These are upcoming auctions that will be displayed on the frontend's upcoming page.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime
import logging

from scrapers.base import BaseScraper
from config import settings


class TreasuryScraper(BaseScraper):
    """Scraper for Treasury.gov real estate auction listings"""
    
    def __init__(self):
        super().__init__()
        self.base_url = settings.treasury_base_url
        self.listing_url = settings.treasury_listing_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_source_name(self) -> str:
        return 'treasury'
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all auction items from Treasury.gov real property page"""
        html = self.fetch_listing_page()
        if not html:
            return []
        
        items = self.parse_listing_page(html)
        
        # Enrich items with detail page data if available
        enriched_items = []
        for item in items:
            if item.get('item_url'):
                details = self.scrape_detail_page(item['item_url'])
                if details:
                    item.update(details)
            
            # Standardize first (this generates lot_number), then validate
            standardized = self.standardize_item(item)
            if self.validate_item(standardized):
                enriched_items.append(standardized)
        
        self.logger.info(f"Successfully scraped {len(enriched_items)} items from Treasury.gov")
        return enriched_items
    
    def scrape_single(self, item_id: str) -> Optional[Dict]:
        """
        Scrape a single auction item by its ID (sale number).
        Not commonly used since we scrape the full listing.
        """
        # For Treasury.gov, we'd need the detail page URL
        # Since we don't have a direct ID->URL mapping, return None
        self.logger.warning(f"scrape_single not implemented for Treasury scraper")
        return None
    
    def fetch_listing_page(self) -> Optional[str]:
        """Fetch the main listing page HTML"""
        try:
            self.logger.info(f"Fetching Treasury.gov listing page: {self.listing_url}")
            response = self.session.get(
                self.listing_url,
                timeout=settings.request_timeout
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching listing page: {e}")
            return None
    
    def parse_listing_page(self, html: str) -> List[Dict]:
        """Parse the listing page to extract basic auction information"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        try:
            # Find all table rows containing auction listings
            # Looking for rows with property information
            main_table = soup.find('table', {'width': '800'})
            if not main_table:
                self.logger.error("Could not find main auction table")
                return []
            
            # Find all rows that contain auction data
            rows = main_table.find_all('tr')
            
            current_item = None
            for row in rows:
                # Look for property address (main identifier) - in <p class="style1">
                address_cell = row.find('p', class_='style1')
                if address_cell:
                    # Get property type (SINGLE FAMILY HOME, etc.) - in <font size="3" color="#cc0000"><b>
                    property_type = ''
                    type_tag = address_cell.find('font', {'color': '#cc0000', 'size': '3'})
                    if type_tag:
                        property_type = type_tag.get_text(strip=True)
                    
                    # Get full address - in <span class="style12"><font color="#cc0000">
                    full_address = ''
                    address_span = address_cell.find('span', class_='style12')
                    if address_span:
                        address_font = address_span.find('font', {'color': '#cc0000'})
                        if address_font:
                            full_address = address_font.get_text(strip=True)
                    
                    # Need both property type and address to proceed
                    if not property_type or not full_address:
                        continue
                    
                    # Build title combining type and address
                    title = f"{property_type}: {full_address}"
                    
                    # Save previous item if exists
                    if current_item and current_item.get('title'):
                        items.append(current_item)
                    
                    # Start new item
                    current_item = {
                        'title': title,
                        'location_address': full_address,
                        'description': '',
                        'asset_type': 'real-estate',
                        'extra_data': {'property_type': property_type}
                    }
                    
                    # Extract city and state from address
                    location_match = re.search(r',\s*([^,]+),\s*([A-Z]{2})\s*\d', full_address)
                    if location_match:
                        current_item['location_city'] = location_match.group(1).strip()
                        current_item['location_state'] = location_match.group(2).strip()
                    
                    # Get auction date - look for "Friday, January 30, 2026" pattern in nested fonts
                    date_text = ''
                    for strong_tag in address_cell.find_all('strong'):
                        text = strong_tag.get_text(strip=True)
                        if re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\w+\s+\d+,\s+\d{4}', text):
                            date_text = text
                            break
                    
                    if date_text:
                        try:
                            current_item['closing_date'] = datetime.strptime(date_text, '%A, %B %d, %Y')
                        except ValueError as e:
                            self.logger.warning(f"Could not parse date '{date_text}': {e}")
                
                # Look for description and sale number - in <p><span class="style11">
                if current_item:
                    desc_cell = row.find('span', class_='style11')
                    if desc_cell:
                        desc_text = desc_cell.get_text(separator=' ', strip=True)
                        # Extract sale number
                        sale_match = re.search(r'Sale\s*#\s*([\d-]+)', desc_text)
                        if sale_match:
                            current_item['sale_number'] = sale_match.group(1).strip()
                        # Store description (remove sale number from it)
                        desc_clean = re.sub(r'Sale\s*#\s*[\d-]+\.?', '', desc_text).strip()
                        current_item['description'] = desc_clean
                
                # Look for property images and detail page links
                if current_item:
                    image_cell = row.find('td', height='182')
                    if image_cell:
                        link = image_cell.find('a')
                        if link:
                            href = link.get('href')
                            if href and isinstance(href, str):
                                detail_url = href
                                if not detail_url.startswith('http'):
                                    detail_url = self.base_url + '/' + detail_url.lstrip('/')
                                current_item['item_url'] = detail_url
                        
                        img = image_cell.find('img')
                        if img:
                            src = img.get('src')
                            if src and isinstance(src, str):
                                img_url = src
                                if not img_url.startswith('http'):
                                    img_url = self.base_url + '/' + img_url.lstrip('/')
                                current_item['image_urls'] = [img_url]
            
            # Add the last item
            if current_item and current_item.get('title'):
                items.append(current_item)
            
            # Deduplicate by sale_number (properties may appear in multiple month sections)
            seen_sales = {}
            unique_items = []
            for item in items:
                sale_num = item.get('sale_number')
                if sale_num and sale_num not in seen_sales:
                    seen_sales[sale_num] = True
                    unique_items.append(item)
                elif not sale_num:
                    # Include items without sale numbers
                    unique_items.append(item)
            
            self.logger.info(f"Parsed {len(unique_items)} unique auction items from listing page (removed {len(items) - len(unique_items)} duplicates)")
            
        except Exception as e:
            self.logger.error(f"Error parsing listing page: {e}", exc_info=True)
        
        return unique_items if 'unique_items' in locals() else []
    
    def _extract_listing_details(self, item: Dict, text_content: str):
        """Extract details from the listing text content"""
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract auction date
            if 'Auction Date and Time:' in line or 'ONLINE AUCTION' in line:
                date_match = re.search(r'(\w+,\s+\w+\s+\d+,\s+\d{4})', line)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        item['closing_date'] = datetime.strptime(date_str, '%A, %B %d, %Y')
                    except ValueError:
                        try:
                            item['closing_date'] = datetime.strptime(date_str, '%B %d, %Y')
                        except ValueError:
                            pass
            
            # Extract deposit
            if 'Deposit:' in line:
                deposit_match = re.search(r'\$[\d,]+', line)
                if deposit_match:
                    item['extra_data']['deposit'] = deposit_match.group(0)
            
            # Extract starting bid
            if 'Starting Bid:' in line:
                bid_match = re.search(r'\$[\d,]+', line)
                if bid_match:
                    bid_str = bid_match.group(0).replace('$', '').replace(',', '')
                    try:
                        item['minimum_bid'] = float(bid_str)
                    except ValueError:
                        pass
            
            # Extract inspection date
            if 'Inspections:' in line or 'Inspection:' in line:
                item['extra_data']['inspection_date'] = line.split(':', 1)[1].strip()
            
            # Extract sale number (handles both "Sale #" and "Sale Number:" formats)
            if 'Sale #' in line or 'Sale Number:' in line:
                sale_match = re.search(r'(?:Sale\s*#|Sale\s*Number:?)\s*([\d-]+)', line, re.IGNORECASE)
                if sale_match:
                    item['sale_number'] = sale_match.group(1).strip()
            
            # Build description
            if any(keyword in line for keyword in ['SINGLE FAMILY', 'MULTI-FAMILY', 'CONDO', 'TOWNHOME', 'COMMERCIAL', 'LAND', 'LOT']):
                if item['description']:
                    item['description'] += ' ' + line
                else:
                    item['description'] = line
    
    def scrape_detail_page(self, detail_url: str) -> Optional[Dict]:
        """Scrape the detail page for additional property information"""
        try:
            self.logger.info(f"Fetching detail page: {detail_url}")
            response = self.session.get(
                detail_url,
                timeout=settings.request_timeout
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            details = {'extra_data': {}}
            
            # Extract property details from the detail page table
            detail_table = soup.find('table', {'width': '272'})
            if detail_table:
                rows = detail_table.find_all('tr')
                for row in rows:
                    cell = row.find('td')
                    if cell:
                        text = cell.get_text(strip=True)
                        
                        # Living space
                        if 'Living Space:' in text:
                            space_match = re.search(r'Living Space:\s*([\d,]+\s*±?\s*sq\.\s*ft\.)', text)
                            if space_match:
                                details['extra_data']['living_space'] = space_match.group(1)
                        
                        # Site area
                        if 'Site Area:' in text:
                            area_match = re.search(r'Site Area:\s*([\d,]+\s*±?\s*sq\.\s*ft\.)', text)
                            if area_match:
                                details['extra_data']['site_area'] = area_match.group(1)
                        
                        # Year built
                        if 'Year Built:' in text:
                            year_match = re.search(r'Year Built:\s*(\d{4})', text)
                            if year_match:
                                details['extra_data']['year_built'] = year_match.group(1)
                        
                        # County
                        if 'County:' in text:
                            county_match = re.search(r'County:\s*([^\n]+)', text)
                            if county_match:
                                details['extra_data']['county'] = county_match.group(1).strip()
                        
                        # County taxes
                        if 'County Taxes:' in text:
                            tax_match = re.search(r'\$[\d,]+\.\d{2}', text)
                            if tax_match:
                                details['extra_data']['county_taxes'] = tax_match.group(0)
                        
                        # Zoning
                        if 'Zoning:' in text:
                            zoning_match = re.search(r'Zoning:\s*([^\n]+)', text)
                            if zoning_match:
                                details['extra_data']['zoning'] = zoning_match.group(1).strip()
                        
                        # Parcel number
                        if 'Parcel' in text and 'No' in text:
                            parcel_match = re.search(r'Parcel\s*No:\s*(\d+)', text)
                            if parcel_match:
                                details['extra_data']['parcel_number'] = parcel_match.group(1)
                        
                        # Utilities
                        if 'Utilities:' in text:
                            utilities_match = re.search(r'Utilities:\s*([^\n]+)', text)
                            if utilities_match:
                                details['extra_data']['utilities'] = utilities_match.group(1).strip()
                        
                        # Sale number (handles both "Sale #" and "Sale Number:" formats)
                        if 'Sale #' in text or 'Sale Number:' in text:
                            sale_match = re.search(r'(?:Sale\s*#|Sale\s*Number:?)\s*([\d-]+)', text, re.IGNORECASE)
                            if sale_match:
                                details['sale_number'] = sale_match.group(1).strip()
            
            # Extract full description
            description_p = soup.find('p', class_='style10')
            if description_p:
                desc_text = description_p.get_text(separator=' ', strip=True)
                # Clean up the description
                desc_text = re.sub(r'\s+', ' ', desc_text)
                if desc_text:
                    details['description'] = desc_text
            
            # Extract auction details from table rows - search all text on page
            page_text = soup.get_text()
            
            # Extract auction date and time
            date_match = re.search(r'Auction\s+Date\s+and\s+Time:\s*(\w+,\s+\w+\s+\d+,\s+\d{4})\s+from\s+([\d:-]+\s*[AP]M)', page_text)
            if date_match:
                date_str = date_match.group(1)
                time_str = date_match.group(2)
                details['extra_data']['auction_time'] = f"{date_str} at {time_str}"
                try:
                    details['closing_date'] = datetime.strptime(date_str, '%A, %B %d, %Y')
                except ValueError:
                    pass
            
            # Extract deposit - look for pattern "Deposit: $XX,XXX"
            deposit_match = re.search(r'Deposit:\s*\$[\d,]+', page_text)
            if deposit_match:
                details['extra_data']['deposit'] = deposit_match.group(0).split(':')[1].strip()
            
            # Extract starting bid - look for pattern "Starting Bid: $XX,XXX"
            starting_match = re.search(r'Starting\s+Bid:\s*\$[\d,]+', page_text)
            if starting_match:
                bid_str = starting_match.group(0).split(':')[1].strip().replace('$', '').replace(',', '')
                try:
                    details['minimum_bid'] = float(bid_str)
                except ValueError:
                    pass
            
            # Extract inspection times
            inspection_match = re.search(r'Inspections?:\s*([^\n]+)', page_text)
            if inspection_match:
                details['extra_data']['inspection_times'] = inspection_match.group(1).strip()
            
            # Extract all images from the detail page
            images = []
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if src and isinstance(src, str):
                    if not any(skip in src for skip in ['spacer', 'type_', 'images/type']):
                        if not src.startswith('http'):
                            src = self.base_url + '/' + src.lstrip('/')
                        images.append(src)
            
            if images:
                details['image_urls'] = images
            
            return details
            
        except Exception as e:
            self.logger.error(f"Error scraping detail page {detail_url}: {e}", exc_info=True)
            return None
    
    def standardize_item(self, item: Dict) -> Dict:
        """Standardize the item format to match the database schema"""
        standardized = {
            'source': 'treasury',
            'asset_type': 'real-estate',
            'status': 'upcoming',  # Treasury auctions are upcoming, not active yet
            'title': item.get('title', 'Treasury Real Estate Auction'),
            'description': item.get('description', 'Currently not available'),
            'location_address': item.get('location_address', 'Currently not available'),
            'location_city': item.get('location_city', 'Currently not available'),
            'location_state': item.get('location_state'),
            'minimum_bid': item.get('minimum_bid'),
            'closing_date': item.get('closing_date'),
            'item_url': item.get('item_url', ''),
            'image_urls': item.get('image_urls', []),
            'sale_number': item.get('sale_number', ''),
            'extra_data': item.get('extra_data', {}),
            'quantity': 1,
            'is_available': True,
        }
        
        # Create lot_number (unique identifier)
        if standardized['sale_number']:
            standardized['lot_number'] = f"treasury-{standardized['sale_number']}"
        else:
            # Fallback: use a hash of the title and address
            import hashlib
            unique_str = f"{standardized['title']}-{standardized['location_address']}"
            hash_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
            standardized['lot_number'] = f"treasury-{hash_id}"
        
        # Add agency information
        standardized['agency'] = 'US Department of Treasury'
        
        return standardized
