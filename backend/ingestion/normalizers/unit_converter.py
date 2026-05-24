"""
Unit conversion utilities for normalizing source data.

Handles the messy reality of unit inconsistencies across SAP exports
(L, LTR, Liter, l, GAL, KG, M3), utility data (kWh, MWh, therms),
and travel data (km, miles).

Design decision: normalize to a canonical set of units that match
DEFRA emission factor units. This avoids double-conversion errors.
"""
import re
from decimal import Decimal, InvalidOperation


# Canonical unit mappings: maps various spellings to canonical form
VOLUME_UNIT_MAP = {
    'L': 'L', 'l': 'L', 'LTR': 'L', 'Liter': 'L', 'liter': 'L',
    'liters': 'L', 'Liters': 'L', 'LITER': 'L', 'Lt': 'L', 'lt': 'L',
    'GAL': 'GAL', 'gal': 'GAL', 'Gallon': 'GAL', 'gallon': 'GAL',
    'gallons': 'GAL', 'Gallons': 'GAL', 'US_GAL': 'GAL',
    'KG': 'KG', 'kg': 'KG', 'Kg': 'KG', 'kilogram': 'KG',
    'M3': 'M3', 'm3': 'M3', 'CBM': 'M3', 'cubicmeter': 'M3',
    'BBL': 'BBL', 'bbl': 'BBL', 'barrel': 'BBL',
    'TO': 'TO', 'MT': 'TO', 'tonne': 'TO', 'metric_ton': 'TO',
}

ENERGY_UNIT_MAP = {
    'kWh': 'kWh', 'kwh': 'kWh', 'KWH': 'kWh', 'Kwh': 'kWh',
    'MWh': 'MWh', 'mwh': 'MWh', 'MWH': 'MWh',
    'GJ': 'GJ', 'gj': 'GJ', 'gigajoule': 'GJ',
    'therm': 'therm', 'therms': 'therm', 'Therm': 'therm', 'THERM': 'therm',
}

DISTANCE_UNIT_MAP = {
    'km': 'km', 'KM': 'km', 'Km': 'km', 'kilometer': 'km', 'kilometers': 'km',
    'mi': 'mi', 'MI': 'mi', 'mile': 'mi', 'miles': 'mi', 'Miles': 'mi',
}

# Conversion factors TO canonical units
# Fuel volumes → Liters
VOLUME_TO_LITERS = {
    'L': Decimal('1'),
    'GAL': Decimal('3.78541'),     # US gallon
    'M3': Decimal('1000'),         # cubic meter
    'BBL': Decimal('158.987'),     # barrel (42 US gallons)
}

# Energy → kWh
ENERGY_TO_KWH = {
    'kWh': Decimal('1'),
    'MWh': Decimal('1000'),
    'GJ': Decimal('277.778'),
    'therm': Decimal('29.3071'),
}

# Distance → km
DISTANCE_TO_KM = {
    'km': Decimal('1'),
    'mi': Decimal('1.60934'),
}


def normalize_unit(raw_unit: str) -> tuple[str, str]:
    """
    Normalize a raw unit string to its canonical form and category.
    
    Returns: (canonical_unit, category) where category is 'volume', 'energy', 'distance', or 'unknown'
    """
    cleaned = raw_unit.strip()
    
    if cleaned in VOLUME_UNIT_MAP:
        return VOLUME_UNIT_MAP[cleaned], 'volume'
    if cleaned in ENERGY_UNIT_MAP:
        return ENERGY_UNIT_MAP[cleaned], 'energy'
    if cleaned in DISTANCE_UNIT_MAP:
        return DISTANCE_UNIT_MAP[cleaned], 'distance'
    
    return cleaned, 'unknown'


def convert_to_canonical(value: Decimal, from_unit: str, target_unit: str = None) -> tuple[Decimal, str]:
    """
    Convert a value from its source unit to the canonical unit for its category.
    
    For volume: converts to Liters
    For energy: converts to kWh
    For distance: converts to km
    
    Returns: (converted_value, canonical_unit)
    """
    canonical, category = normalize_unit(from_unit)
    
    if category == 'volume':
        target = target_unit or 'L'
        if canonical in VOLUME_TO_LITERS:
            liters = value * VOLUME_TO_LITERS[canonical]
            if target == 'L':
                return liters, 'L'
            # Convert from liters to target
            for unit, factor in VOLUME_TO_LITERS.items():
                if unit == target:
                    return liters / factor, target
        return value, canonical
    
    elif category == 'energy':
        target = target_unit or 'kWh'
        if canonical in ENERGY_TO_KWH:
            kwh = value * ENERGY_TO_KWH[canonical]
            if target == 'kWh':
                return kwh, 'kWh'
            for unit, factor in ENERGY_TO_KWH.items():
                if unit == target:
                    return kwh / factor, target
        return value, canonical
    
    elif category == 'distance':
        target = target_unit or 'km'
        if canonical in DISTANCE_TO_KM:
            km = value * DISTANCE_TO_KM[canonical]
            if target == 'km':
                return km, 'km'
        return value, canonical
    
    return value, canonical


def parse_german_decimal(value_str: str) -> Decimal:
    """
    Parse a German-format number (dot as thousands separator, comma as decimal).
    
    Examples:
        '1.234,56' → Decimal('1234.56')
        '5.000,000' → Decimal('5000.000')
        '4,25' → Decimal('4.25')
        '1234' → Decimal('1234')
    """
    if not value_str or not isinstance(value_str, str):
        raise ValueError(f"Cannot parse empty or non-string value: {value_str!r}")
    
    cleaned = value_str.strip()
    
    # Detect German format: has both dot and comma, with comma after last dot
    has_comma = ',' in cleaned
    has_dot = '.' in cleaned
    
    if has_comma and has_dot:
        # German format: dots are thousands separators, comma is decimal
        last_comma = cleaned.rfind(',')
        last_dot = cleaned.rfind('.')
        
        if last_comma > last_dot:
            # German: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US: 1,234.56
            cleaned = cleaned.replace(',', '')
    elif has_comma and not has_dot:
        # Could be German decimal (4,25) or thousands separator
        # If comma is near the end with 1-6 digits after, treat as decimal
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) <= 6:
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Cannot parse number: {value_str!r}")


def parse_number(value_str: str) -> Decimal:
    """
    Parse a number that might be in US or German format.
    Tries standard parsing first, falls back to German format.
    """
    if isinstance(value_str, (int, float)):
        return Decimal(str(value_str))
    
    if not isinstance(value_str, str):
        raise ValueError(f"Cannot parse: {value_str!r}")
    
    cleaned = value_str.strip()
    if not cleaned:
        raise ValueError("Empty string")
    
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[€$£¥\s]', '', cleaned)
    
    return parse_german_decimal(cleaned)
