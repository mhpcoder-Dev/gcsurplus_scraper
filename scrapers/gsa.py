"""
GSA Auctions scraper - fetches US government surplus auctions from GSA API.
Migrated from Next.js to centralize all data fetching in FastAPI.
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import os
import pytz
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from scrapers.base import BaseScraper


class GSAScraper(BaseScraper):
    """Scraper for GSA Auctions API"""
    
    def __init__(self):
        super().__init__()
        self.api_base = os.getenv('GSA_API_BASE_URL', 'https://api.gsa.gov/assets/gsaauctions/v2')
        self.api_key = os.getenv('GSA_API_KEY', 'rXyfDnTjMh3d0Zu56fNcMbHb5dgFBQrmzfTjZqq3')
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'MoneyMeta-AuctionExplorer/1.0'
        })
        # Rate limiting: 60 requests per 60 seconds (1 req/sec)
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds
        # Selenium driver (lazy initialization)
        self.driver = None
        self.driver_init_attempted = False  # Track if we already tried to init driver
    
    def get_source_name(self) -> str:
        return 'gsa'
    
    def _get_driver(self):
        """Get or create Selenium WebDriver (tries Edge first, then Chrome)"""
        # If already attempted and failed, don't try again
        if self.driver_init_attempted and self.driver is None:
            return None
            
        if self.driver is None:
            self.driver_init_attempted = True
            
            # Try Microsoft Edge first (pre-installed on Windows)
            try:
                edge_options = EdgeOptions()
                edge_options.add_argument('--headless=new')
                edge_options.add_argument('--no-sandbox')
                edge_options.add_argument('--disable-dev-shm-usage')
                edge_options.add_argument('--disable-gpu')
                edge_options.add_argument('--window-size=1920,1080')
                edge_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Suppress DevTools logging
                
                # Try using system Edge driver first (no internet required)
                try:
                    self.driver = webdriver.Edge(options=edge_options)
                    self.logger.info("✓ Selenium WebDriver initialized (headless Edge - system driver)")
                    return self.driver
                except:
                    # Fallback to webdriver-manager (requires internet)
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=service, options=edge_options)
                    self.logger.info("✓ Selenium WebDriver initialized (headless Edge - downloaded driver)")
                    return self.driver
            except Exception as e:
                self.logger.debug(f"Edge WebDriver failed: {str(e)[:100]}")
            
            # Fallback to Chrome
            try:
                chrome_options = ChromeOptions()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
                
                # Try system Chrome driver first
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                    self.logger.info("✓ Selenium WebDriver initialized (headless Chrome - system driver)")
                    return self.driver
                except:
                    service = ChromeService(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info("✓ Selenium WebDriver initialized (headless Chrome - downloaded driver)")
                    return self.driver
            except Exception as e:
                self.logger.info(f"⚠ Selenium unavailable (Edge/Chrome issue). Using state-based timezone inference as fallback.")
                self.logger.debug(f"Driver error: {str(e)[:150]}")
                self.driver = None
        return self.driver
    
    def _close_driver(self):
        """Close Selenium WebDriver"""
        if self.driver is not None:
            try:
                self.driver.quit()
                self.logger.info("Selenium WebDriver closed")
            except:
                pass
            finally:
                self.driver = None
    
    def _rate_limit(self):
        """Enforce rate limiting of 1 request per second"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def scrape_all(self) -> List[Dict]:
        """Fetch all auction items from GSA API"""
        try:
            self._rate_limit()
            
            self.logger.info("=" * 60)
            self.logger.info("Starting GSA scraper with Selenium-based timezone parsing")
            self.logger.info("=" * 60)
            
            url = f"{self.api_base}/auctions"
            params = {
                'api_key': self.api_key,
                'format': 'JSON'
            }
            
            self.logger.info(f"Fetching data from GSA API")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.logger.info(f"GSA API response received")
            
            # Parse response based on structure
            items = []
            if data and data.get('Results') and isinstance(data['Results'], list):
                items = data['Results']
            elif data and isinstance(data, list):
                items = data
            elif data and data.get('auctions') and isinstance(data['auctions'], list):
                items = data['auctions']
            elif data and data.get('results') and isinstance(data['results'], list):
                items = data['results']
            else:
                self.logger.warning(f"Unexpected GSA API response structure: {list(data.keys()) if data else 'null'}")
                return []
            
            # Transform items to our standard format
            standardized_items = []
            for item in items:
                try:
                    transformed = self.transform_gsa_item(item)
                    if self.validate_item(transformed):
                        standardized_items.append(self.standardize_item(transformed))
                except Exception as e:
                    self.logger.error(f"Error transforming GSA item: {e}")
                    continue
            
            self.logger.info(f"Successfully processed {len(standardized_items)} items from GSA")
            return standardized_items
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching from GSA API: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in GSA scraper: {e}")
            return []
        finally:
            # Close Selenium driver after scraping is complete
            self._close_driver()
    
    def scrape_single(self, item_id: str) -> Optional[Dict]:
        """Fetch a single item by sale_no-lot_no format"""
        try:
            self._rate_limit()
            
            # Parse item_id as "saleNo-lotNo"
            if '-' in item_id:
                sale_no, lot_no = item_id.split('-', 1)
            else:
                self.logger.warning(f"Invalid GSA item ID format: {item_id}")
                return None
            
            url = f"{self.api_base}/auctions"
            params = {
                'api_key': self.api_key,
                'format': 'JSON',
                'saleNo': sale_no,
                'lotNo': lot_no
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Get first result
            items = []
            if data and data.get('Results') and isinstance(data['Results'], list):
                items = data['Results']
            elif data and isinstance(data, list):
                items = data
            
            if items:
                transformed = self.transform_gsa_item(items[0])
                return self.standardize_item(transformed) if self.validate_item(transformed) else None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching single GSA item: {e}")
            return None
    
    def transform_gsa_item(self, item: Dict) -> Dict:
        """Transform GSA API response to our standard format"""
        
        # Extract location information
        location_city = item.get('propertyCity', '') or ''
        location_state = item.get('propertyState', '') or ''
        sale_city = item.get('locationCity', '') or location_city
        sale_state = item.get('locationST', '') or location_state
        
        # Build address
        location_address = ' '.join(filter(None, [
            item.get('propertyAddr1', ''),
            item.get('propertyAddr2', ''),
            item.get('propertyAddr3', '')
        ])).strip()
        
        # Extract images
        image_urls = []
        if item.get('imageURL'):
            image_urls = [item['imageURL']]
        
        # Classify asset type
        asset_type = self.classify_asset_type(item)
        
        # Build item URL
        item_url = item.get('itemDescURL') or f"https://www.gsaauctions.gov/gsaauctions/aucitsrh/?sl={item.get('saleNo', '')}"
        
        # Determine status
        auction_status = item.get('auctionStatus', '').lower()
        status = 'active'
        is_active = auction_status == 'active'
        is_future = auction_status in ['scheduled', ' ']
        is_preview = auction_status == 'preview'
        
        if auction_status in ['closed', 'ended', 'sold']:
            status = 'closed'
        elif auction_status == 'expired':
            status = 'expired'
        
        # Parse dates - try to get accurate closing time from detail page with Selenium
        closing_date = None
        if item_url and is_active:
            # For active auctions, fetch the detail page with Selenium to get accurate closing time
            closing_date = self.parse_closing_time_with_selenium(item_url)
        
        # Fallback to API date with state-based timezone if Selenium parsing failed
        if not closing_date:
            closing_date = self.parse_gsa_date_with_location(
                item.get('aucEndDt'),
                location_state
            )
        
        bid_date = self.parse_gsa_date_with_location(item.get('aucStartDt'), location_state)
        
        return {
            'lot_number': f"{item.get('saleNo', '')}-{item.get('lotNo', '')}",
            'sale_number': item.get('saleNo'),
            'title': item.get('itemName', 'GSA Auction Item'),
            'description': item.get('lotInfo', ''),
            'current_bid': float(item.get('highBidAmount', 0)) if item.get('highBidAmount') else 0.0,
            'minimum_bid': float(item.get('reserve', 0)) if item.get('reserve') else None,
            'bid_increment': float(item.get('aucIncrement', 0)) if item.get('aucIncrement') else None,
            'currency': 'USD',
            'quantity': 1,
            'status': status,
            'is_available': is_active or is_future or is_preview,
            'city': location_city,
            'region': location_state,
            'country': 'USA',
            'postal_code': item.get('propertyZip', ''),
            'address_raw': location_address,
            'closing_date': closing_date,
            'bid_date': bid_date,
            'image_urls': image_urls,
            'contact_name': item.get('contractOfficer'),
            'contact_phone': item.get('coPhone'),
            'contact_email': item.get('coEmail'),
            'agency': item.get('agencyName') or item.get('bureauName') or 'GSA',
            'asset_type': asset_type,
            'item_url': item_url,
            'source': 'gsa',
            # Additional GSA-specific fields
            'extra_data': {
                'agency_code': item.get('agencyCode'),
                'bureau_code': item.get('bureauCode'),
                'sale_city': sale_city,
                'sale_state': sale_state,
                'inactivity_time': item.get('inactivityTime'),
                'instructions': item.get('instruction'),
                'bidders_count': item.get('biddersCount', 0),
                'is_active': is_active,
                'is_future': is_future,
                'is_preview': is_preview
            }
        }
    
    def classify_asset_type(self, item: Dict) -> str:
        """Classify item into asset type categories"""
        item_name = (item.get('itemName') or '').lower()
        lot_info = (item.get('lotInfo') or '').lower()
        text = f"{item_name} {lot_info}"
        
        # Real estate and land
        if any(keyword in text for keyword in [
            'real estate', 'land', 'building', 'property', 'warehouse', 
            'office', 'facility', 'acre', 'commercial', 'residential'
        ]):
            return 'real-estate'
        
        # Vehicles
        if any(keyword in text for keyword in [
            'vehicle', 'car', 'truck', 'van', 'suv', 'sedan', 'pickup', 'automobile', 'auto'
        ]):
            return 'cars'
        
        if any(keyword in text for keyword in ['trailer', 'semi', 'tractor', 'flatbed']):
            return 'trailers'
        
        if any(keyword in text for keyword in ['motorcycle', 'bike', 'scooter', 'harley', 'honda', 'yamaha']):
            return 'motorcycles'
        
        # Electronics
        if any(keyword in text for keyword in [
            'computer', 'laptop', 'tablet', 'phone', 'electronic', 
            'equipment', 'server', 'monitor'
        ]):
            return 'electronics'
        
        # Industrial
        if any(keyword in text for keyword in [
            'industrial', 'machinery', 'equipment', 'tool', 
            'generator', 'compressor', 'forklift'
        ]):
            return 'industrial'
        
        # Furniture
        if any(keyword in text for keyword in [
            'furniture', 'desk', 'chair', 'table', 'cabinet', 'office furniture'
        ]):
            return 'furniture'
        
        # Collectibles
        if any(keyword in text for keyword in [
            'coin', 'stamp', 'art', 'collectible', 'antique', 'vintage'
        ]):
            return 'collectibles'
        
        return 'other'
    
    def parse_closing_time_with_selenium(self, item_url: str) -> Optional[datetime]:
        """
        Parse closing time with timezone from GSA detail page using Selenium.
        GSA uses React SPA, so we need JavaScript execution to see the content.
        Format: "01/16/2026 06:30 PM CT"
        """
        try:
            driver = self._get_driver()
            if driver is None:
                return None
            
            self._rate_limit()
            
            self.logger.info(f"Fetching detail page with Selenium: {item_url}")
            driver.get(item_url)
            
            # Wait for page to load (JavaScript needs time to render)
            time.sleep(3)
            
            # Try to find "Closing Time" text in the page
            # Format: <b>Closing Time </b>...</span>01/13/2026 02:04PM CT</li>
            page_source = driver.page_source
            
            # Extract datetime and timezone using regex
            # More specific pattern to avoid matching start time or other dates
            match = re.search(
                r'<b>Closing Time\s*</b>.*?(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}[AP]M)\s+([A-Z]{2,3})',
                page_source,
                re.IGNORECASE | re.DOTALL
            )
            
            if match:
                date_str = match.group(1)  # "01/16/2026"
                time_str = match.group(2)  # "06:13PM" (no space before AM/PM)
                tz_abbr = match.group(3)   # "CT", "ET", "PT", "MT"
                
                self.logger.info(f"Parsed closing time: {date_str} {time_str} {tz_abbr}")
                
                # Parse the datetime (format: MM/DD/YYYY HH:MMAM/PM - no space before AM/PM)
                dt_str = f"{date_str} {time_str}"
                dt = datetime.strptime(dt_str, '%m/%d/%Y %I:%M%p')
                
                # Convert timezone abbreviation to pytz timezone
                tz_map = {
                    'ET': pytz.timezone('US/Eastern'),
                    'EST': pytz.timezone('US/Eastern'),
                    'EDT': pytz.timezone('US/Eastern'),
                    'CT': pytz.timezone('US/Central'),
                    'CST': pytz.timezone('US/Central'),
                    'CDT': pytz.timezone('US/Central'),
                    'MT': pytz.timezone('US/Mountain'),
                    'MST': pytz.timezone('US/Mountain'),
                    'MDT': pytz.timezone('US/Mountain'),
                    'PT': pytz.timezone('US/Pacific'),
                    'PST': pytz.timezone('US/Pacific'),
                    'PDT': pytz.timezone('US/Pacific'),
                }
                
                source_tz = tz_map.get(tz_abbr, pytz.timezone('US/Eastern'))
                
                # Localize to source timezone
                localized_dt = source_tz.localize(dt)
                
                # Convert to UTC and make naive
                utc_dt = localized_dt.astimezone(pytz.UTC).replace(tzinfo=None)
                
                self.logger.info(f"Converted to UTC: {utc_dt}")
                return utc_dt
            else:
                self.logger.warning(f"Could not find closing time pattern in page: {item_url}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error parsing closing time with Selenium: {e}")
            return None
    
    def get_timezone_from_state(self, state: str) -> pytz.tzinfo.BaseTzInfo:
        """
        Determine timezone from US state abbreviation.
        Note: Some states span multiple timezones - using primary timezone.
        """
        # Timezone mapping for US states
        state_to_tz = {
            # Eastern Time
            'CT': 'US/Eastern', 'DE': 'US/Eastern', 'FL': 'US/Eastern',
            'GA': 'US/Eastern', 'MA': 'US/Eastern', 'MD': 'US/Eastern',
            'ME': 'US/Eastern', 'MI': 'US/Eastern', 'NH': 'US/Eastern',
            'NJ': 'US/Eastern', 'NY': 'US/Eastern', 'NC': 'US/Eastern',
            'OH': 'US/Eastern', 'PA': 'US/Eastern', 'RI': 'US/Eastern',
            'SC': 'US/Eastern', 'VT': 'US/Eastern', 'VA': 'US/Eastern',
            'WV': 'US/Eastern', 'DC': 'US/Eastern',
            
            # Central Time
            'AL': 'US/Central', 'AR': 'US/Central', 'IL': 'US/Central',
            'IA': 'US/Central', 'KS': 'US/Central', 'KY': 'US/Central',
            'LA': 'US/Central', 'MN': 'US/Central', 'MS': 'US/Central',
            'MO': 'US/Central', 'NE': 'US/Central', 'ND': 'US/Central',
            'OK': 'US/Central', 'SD': 'US/Central', 'TN': 'US/Central',
            'TX': 'US/Central', 'WI': 'US/Central',
            
            # Mountain Time
            'AZ': 'US/Arizona', 'CO': 'US/Mountain', 'ID': 'US/Mountain',
            'MT': 'US/Mountain', 'NM': 'US/Mountain', 'UT': 'US/Mountain',
            'WY': 'US/Mountain',
            
            # Pacific Time
            'CA': 'US/Pacific', 'NV': 'US/Pacific', 'OR': 'US/Pacific',
            'WA': 'US/Pacific',
            
            # Alaska & Hawaii
            'AK': 'US/Alaska', 'HI': 'US/Hawaii',
        }
        
        tz_name = state_to_tz.get(state.upper(), 'US/Eastern')  # Default to Eastern
        return pytz.timezone(tz_name)
    
    def parse_gsa_date_with_location(self, date_str: Optional[str], state: str) -> Optional[datetime]:
        """
        Parse GSA date and convert to UTC using property state timezone.
        GSA API doesn't include timezone, so we infer it from the property location.
        """
        if not date_str:
            return None
        
        try:
            # Try ISO format first
            from datetime import timezone
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # If timezone-aware, convert to UTC
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            
            # If naive datetime from API, assume it's in the property's timezone
            if state:
                property_tz = self.get_timezone_from_state(state)
                localized_dt = property_tz.localize(dt)
                return localized_dt.astimezone(pytz.UTC).replace(tzinfo=None)
            
            # No state info - assume Eastern Time as fallback
            eastern_tz = pytz.timezone('US/Eastern')
            localized_dt = eastern_tz.localize(dt)
            return localized_dt.astimezone(pytz.UTC).replace(tzinfo=None)
            
        except Exception as e:
            self.logger.debug(f"ISO parsing failed, trying other formats: {e}")
            pass
        
        # Try other common formats
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                if fmt in ['%Y-%m-%d', '%m/%d/%Y']:
                    # Set to end of day
                    dt = dt.replace(hour=23, minute=59, second=59)
                
                # Use property state timezone
                if state:
                    property_tz = self.get_timezone_from_state(state)
                else:
                    property_tz = pytz.timezone('US/Eastern')
                
                localized = property_tz.localize(dt)
                return localized.astimezone(pytz.UTC).replace(tzinfo=None)
            except:
                continue
        
        return None
