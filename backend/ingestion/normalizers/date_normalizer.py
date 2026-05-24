"""
Date normalization utilities.

Handles the variety of date formats encountered in SAP exports,
utility bills, and travel reports. SAP is particularly problematic
with DD.MM.YYYY (German locale) vs YYYY-MM-DD (internal) vs
MM/DD/YYYY (US locale depending on user settings).
"""
from datetime import date, datetime
from typing import Optional

# Date formats to try, in order of likelihood
DATE_FORMATS = [
    '%d.%m.%Y',      # German SAP: 24.05.2024
    '%Y-%m-%d',      # ISO: 2024-05-24
    '%m/%d/%Y',      # US: 05/24/2024
    '%d/%m/%Y',      # UK: 24/05/2024
    '%Y%m%d',        # SAP internal: 20240524
    '%d-%m-%Y',      # Alternative: 24-05-2024
    '%m-%d-%Y',      # Alternative US: 05-24-2024
    '%d %b %Y',      # 24 May 2024
    '%d %B %Y',      # 24 May 2024
    '%b %d, %Y',     # May 24, 2024
    '%B %d, %Y',     # May 24, 2024
]


def parse_date(date_str: str) -> Optional[date]:
    """
    Try multiple date formats to parse a date string.
    Returns None if no format matches.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    cleaned = date_str.strip()
    if not cleaned:
        return None
    
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    
    return None


def parse_date_strict(date_str: str) -> date:
    """
    Parse a date string, raising ValueError if no format matches.
    """
    result = parse_date(date_str)
    if result is None:
        raise ValueError(f"Cannot parse date: {date_str!r}")
    return result
