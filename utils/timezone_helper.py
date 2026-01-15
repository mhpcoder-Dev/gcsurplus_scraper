"""
Enhanced timezone handling utilities for auction scrapers.

Handles multiple timezones from different auction sources:
- GCSurplus (Canada): Eastern Time
- GSA (US): Varies by location (Pacific, Mountain, Central, Eastern)
- Treasury (US): Eastern Time

All dates are converted to UTC for storage.
"""

from datetime import datetime, timedelta
from typing import Optional
import pytz
import re


# Timezone definitions
EASTERN = pytz.timezone('US/Eastern')
CENTRAL = pytz.timezone('US/Central')
MOUNTAIN = pytz.timezone('US/Mountain')
PACIFIC = pytz.timezone('US/Pacific')
UTC = pytz.UTC


# US State to Timezone mapping
STATE_TIMEZONES = {
    # Eastern Time
    'CT': EASTERN, 'DE': EASTERN, 'FL': EASTERN, 'GA': EASTERN, 'IN': EASTERN,
    'KY': EASTERN, 'ME': EASTERN, 'MD': EASTERN, 'MA': EASTERN, 'MI': EASTERN,
    'NH': EASTERN, 'NJ': EASTERN, 'NY': EASTERN, 'NC': EASTERN, 'OH': EASTERN,
    'PA': EASTERN, 'RI': EASTERN, 'SC': EASTERN, 'VT': EASTERN, 'VA': EASTERN,
    'WV': EASTERN,
    
    # Central Time
    'AL': CENTRAL, 'AR': CENTRAL, 'IL': CENTRAL, 'IA': CENTRAL, 'KS': CENTRAL,
    'LA': CENTRAL, 'MN': CENTRAL, 'MS': CENTRAL, 'MO': CENTRAL, 'NE': CENTRAL,
    'ND': CENTRAL, 'OK': CENTRAL, 'SD': CENTRAL, 'TN': CENTRAL, 'TX': CENTRAL,
    'WI': CENTRAL,
    
    # Mountain Time
    'AZ': MOUNTAIN, 'CO': MOUNTAIN, 'ID': MOUNTAIN, 'MT': MOUNTAIN,
    'NM': MOUNTAIN, 'UT': MOUNTAIN, 'WY': MOUNTAIN,
    
    # Pacific Time
    'CA': PACIFIC, 'NV': PACIFIC, 'OR': PACIFIC, 'WA': PACIFIC,
    
    # Alaska & Hawaii (special cases)
    'AK': pytz.timezone('US/Alaska'),
    'HI': pytz.timezone('US/Hawaii'),
}


def get_timezone_by_state(state_code: str) -> pytz.tzinfo:
    """
    Get timezone for a US state code.
    
    Args:
        state_code: Two-letter US state code (e.g., 'CA', 'NY')
    
    Returns:
        pytz timezone object (defaults to Eastern if not found)
    """
    return STATE_TIMEZONES.get(state_code.upper(), EASTERN)


def convert_to_utc(dt: datetime, source_timezone: pytz.tzinfo = EASTERN) -> datetime:
    """
    Convert a naive datetime to UTC from a specific timezone.
    
    Args:
        dt: Naive datetime object (no timezone info)
        source_timezone: Source timezone (default: US/Eastern)
    
    Returns:
        Naive datetime in UTC
    """
    # If already timezone-aware, convert to UTC
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    
    # Localize to source timezone
    localized_dt = source_timezone.localize(dt)
    
    # Convert to UTC and remove timezone info (naive UTC)
    utc_dt = localized_dt.astimezone(UTC).replace(tzinfo=None)
    
    return utc_dt


def parse_date_with_timezone(
    date_str: str,
    date_format: str,
    source_timezone: pytz.tzinfo = EASTERN,
    end_of_day: bool = True
) -> Optional[datetime]:
    """
    Parse a date string and convert to UTC.
    
    Args:
        date_str: Date string to parse
        date_format: strftime format string
        source_timezone: Source timezone for the date
        end_of_day: If True and no time in format, set to 23:59:59
    
    Returns:
        Naive datetime in UTC, or None if parsing fails
    """
    try:
        dt = datetime.strptime(date_str, date_format)
        
        # If date-only format, set to end of day
        if end_of_day and '%H' not in date_format:
            dt = dt.replace(hour=23, minute=59, second=59)
        
        return convert_to_utc(dt, source_timezone)
    
    except (ValueError, TypeError) as e:
        return None


def parse_gsa_date_with_location(
    date_str: str,
    location_state: Optional[str] = None
) -> Optional[datetime]:
    """
    Parse GSA date considering the auction location's timezone.
    
    Args:
        date_str: Date string from GSA API
        location_state: US state code for the auction location
    
    Returns:
        Naive datetime in UTC
    """
    if not date_str:
        return None
    
    # Determine timezone based on location
    if location_state:
        tz = get_timezone_by_state(location_state)
    else:
        tz = EASTERN  # Default to Eastern if location unknown
    
    try:
        # Try ISO format first (may include timezone)
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                return dt.astimezone(UTC).replace(tzinfo=None)
            else:
                return convert_to_utc(dt, tz)
        
        # Try common formats
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                if fmt in ['%Y-%m-%d', '%m/%d/%Y']:
                    dt = dt.replace(hour=23, minute=59, second=59)
                return convert_to_utc(dt, tz)
            except ValueError:
                continue
        
        return None
    
    except Exception as e:
        return None


def parse_gcsurplus_date(date_str: str) -> Optional[datetime]:
    """
    Parse GCSurplus date (always in Eastern Time).
    
    Args:
        date_str: Date string from GCSurplus
    
    Returns:
        Naive datetime in UTC
    """
    return parse_date_with_timezone(
        date_str,
        date_format='%Y-%m-%d',
        source_timezone=EASTERN,
        end_of_day=True
    )


def parse_treasury_date(date_str: str) -> Optional[datetime]:
    """
    Parse Treasury.gov date (always in Eastern Time).
    
    Args:
        date_str: Date string from Treasury.gov (e.g., "Friday, January 30, 2026")
    
    Returns:
        Naive datetime in UTC
    """
    # Try full format with day of week
    result = parse_date_with_timezone(
        date_str,
        date_format='%A, %B %d, %Y',
        source_timezone=EASTERN,
        end_of_day=True
    )
    
    if result:
        return result
    
    # Try without day of week
    return parse_date_with_timezone(
        date_str,
        date_format='%B %d, %Y',
        source_timezone=EASTERN,
        end_of_day=True
    )


# Timezone info for documentation
TIMEZONE_INFO = {
    'gcsurplus': {
        'name': 'GC Surplus (Canada)',
        'timezone': 'US/Eastern (UTC-5/UTC-4)',
        'note': 'All Canadian government auctions use Eastern Time'
    },
    'gsa': {
        'name': 'GSA Auctions (US)',
        'timezone': 'Varies by location',
        'note': 'Timezone determined by auction property location'
    },
    'treasury': {
        'name': 'Treasury.gov (US)',
        'timezone': 'US/Eastern (UTC-5/UTC-4)',
        'note': 'Federal auctions use Eastern Time'
    }
}


def get_source_timezone_info(source: str) -> dict:
    """Get timezone information for an auction source."""
    return TIMEZONE_INFO.get(source.lower(), {
        'name': source,
        'timezone': 'Unknown',
        'note': 'Timezone not configured'
    })
