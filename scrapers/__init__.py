"""
Scrapers package for auction sites.
Each scraper implements the BaseScraper interface.
"""

from scrapers.base import BaseScraper
from scrapers.gcsurplus import GCSurplusScraper
from scrapers.gsa import GSAScraper
from scrapers.treasury import TreasuryScraper
from scrapers.state_dept import StateDeptScraper

__all__ = ['BaseScraper', 'GCSurplusScraper', 'GSAScraper', 'TreasuryScraper', 'StateDeptScraper']
