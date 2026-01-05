"""
Base scraper class that all site-specific scrapers inherit from.
This ensures a consistent interface across all scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all auction scrapers"""
    
    def __init__(self):
        self.source_name = self.get_source_name()
        self.logger = logging.getLogger(f"scraper.{self.source_name}")
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the identifier for this scraper source (e.g., 'gsa', 'gcsurplus')"""
        pass
    
    @abstractmethod
    def scrape_all(self) -> List[Dict]:
        """
        Scrape all available auction items from the source.
        
        Returns:
            List of dictionaries with standardized auction data
        """
        pass
    
    @abstractmethod
    def scrape_single(self, item_id: str) -> Optional[Dict]:
        """
        Scrape a single auction item by its ID.
        
        Args:
            item_id: The unique identifier for the item
            
        Returns:
            Dictionary with standardized auction data or None if not found
        """
        pass
    
    def validate_item(self, item: Dict) -> bool:
        """
        Validate that an item has all required fields.
        
        Args:
            item: Dictionary containing auction item data
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['lot_number', 'title', 'source']
        
        for field in required_fields:
            if field not in item or item[field] is None:
                self.logger.warning(f"Item missing required field: {field}")
                return False
        
        return True
    
    def standardize_item(self, item: Dict) -> Dict:
        """
        Ensure item has all standard fields with default values.
        
        Args:
            item: Raw item data
            
        Returns:
            Standardized item dictionary
        """
        defaults = {
            'sale_number': None,
            'description': '',
            'current_bid': 0.0,
            'minimum_bid': None,
            'bid_increment': None,
            'next_minimum_bid': None,
            'quantity': 1,
            'status': 'active',
            'is_available': True,
            'location_city': '',
            'location_province': '',
            'location_state': '',
            'location_address': '',
            'closing_date': None,
            'bid_date': None,
            'time_remaining': None,
            'image_urls': [],
            'contact_name': None,
            'contact_phone': None,
            'contact_email': None,
            'agency': None,
            'asset_type': 'other',
            'item_url': None,
        }
        
        # Merge defaults with item data
        standardized = {**defaults, **item}
        
        # Ensure source is set
        if 'source' not in standardized or not standardized['source']:
            standardized['source'] = self.source_name
        
        return standardized
