"""
GSA Auctions scraper - fetches US government surplus auctions from GSA API.
Migrated from Next.js to centralize all data fetching in FastAPI.
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import os

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
    
    def get_source_name(self) -> str:
        return 'gsa'
    
    def scrape_all(self) -> List[Dict]:
        """Fetch all auction items from GSA API"""
        try:
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
    
    def scrape_single(self, item_id: str) -> Optional[Dict]:
        """Fetch a single item by sale_no-lot_no format"""
        try:
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
        
        # Parse dates
        closing_date = self.parse_gsa_date(item.get('aucEndDt'))
        bid_date = self.parse_gsa_date(item.get('aucStartDt'))
        
        return {
            'lot_number': f"{item.get('saleNo', '')}-{item.get('lotNo', '')}",
            'sale_number': item.get('saleNo'),
            'title': item.get('itemName', 'GSA Auction Item'),
            'description': item.get('lotInfo', ''),
            'current_bid': float(item.get('highBidAmount', 0)) if item.get('highBidAmount') else 0.0,
            'minimum_bid': float(item.get('reserve', 0)) if item.get('reserve') else None,
            'bid_increment': float(item.get('aucIncrement', 0)) if item.get('aucIncrement') else None,
            'quantity': 1,
            'status': status,
            'is_available': is_active or is_future or is_preview,
            'location_city': location_city,
            'location_state': location_state,
            'location_address': location_address,
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
                'property_zip': item.get('propertyZip'),
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
    
    def parse_gsa_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse GSA date format to datetime"""
        if not date_str:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        
        # Try other common formats
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None
