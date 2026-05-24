"""
Corporate Travel Parser (Scope 3, Category 6).

Handles TMC-style travel report CSV exports combining flights, hotels,
and ground transport. Based on real-world Concur/Navan export formats.

Key features:
- Flight distance calculation from IATA codes (Haversine + 9% uplift)
- Haul classification (short < 3700km, long ≥ 3700km)
- Cabin class → emission factor mapping
- Hotel nights by city/country
- Ground transport by vehicle type
"""
from decimal import Decimal
from typing import Dict, Any, Optional

from ingestion.parsers.base import BaseParser
from ingestion.normalizers.unit_converter import parse_number
from ingestion.normalizers.date_normalizer import parse_date, parse_date_strict
from ingestion.normalizers.distance_calculator import (
    calculate_flight_distance, classify_haul, get_round_trip_multiplier
)
from reference.models import AirportLookup


# Maps common travel report headers to canonical names
TRAVEL_HEADER_MAP = {
    'Report ID': 'report_id',
    'Trip ID': 'report_id',
    'Booking ID': 'report_id',
    'Employee ID': 'employee_id',
    'Traveler ID': 'employee_id',
    'Employee Name': 'employee_name',
    'Traveler Name': 'employee_name',
    'Traveler': 'employee_name',
    'Expense Type': 'expense_type',
    'Booking Type': 'expense_type',
    'Category': 'expense_type',
    'Type': 'expense_type',
    'Transaction Date': 'transaction_date',
    'Date': 'transaction_date',
    'Travel Date': 'transaction_date',
    'Start Date': 'transaction_date',
    'Origin': 'origin',
    'From': 'origin',
    'Departure': 'origin',
    'Origin Airport': 'origin',
    'Destination': 'destination',
    'To': 'destination',
    'Arrival': 'destination',
    'Destination Airport': 'destination',
    'Cabin Class': 'cabin_class',
    'Class': 'cabin_class',
    'Class of Service': 'cabin_class',
    'Travel Class': 'cabin_class',
    'Route Type': 'route_type',
    'Trip Type': 'route_type',
    'Nights': 'nights',
    'Number of Nights': 'nights',
    'Hotel Nights': 'nights',
    'Duration': 'nights',
    'Vehicle Type': 'vehicle_type',
    'Car Type': 'vehicle_type',
    'Car Class': 'vehicle_type',
    'Distance (km)': 'distance_km',
    'Distance': 'distance_km',
    'Miles': 'distance_miles',
    'Amount': 'amount',
    'Total': 'amount',
    'Cost': 'amount',
    'Transaction Amount': 'amount',
    'Currency': 'currency',
    'Hotel City': 'hotel_location',
    'Hotel Location': 'hotel_location',
    'Hotel': 'hotel_location',
    'Location': 'hotel_location',
    'City': 'hotel_location',
}

# Maps expense type strings to travel categories
EXPENSE_TYPE_MAP = {
    'airfare': 'flight',
    'air': 'flight',
    'flight': 'flight',
    'flights': 'flight',
    'air travel': 'flight',
    'airline': 'flight',
    'hotel': 'hotel',
    'hotel room': 'hotel',
    'lodging': 'hotel',
    'accommodation': 'hotel',
    'car rental': 'car',
    'rental car': 'car',
    'car hire': 'car',
    'taxi': 'taxi',
    'cab': 'taxi',
    'ride': 'taxi',
    'rideshare': 'taxi',
    'uber': 'taxi',
    'ground transport': 'car',
    'ground transportation': 'car',
    'rail': 'rail',
    'train': 'rail',
}

# Maps cabin class to emission factor sub-type
CABIN_CLASS_MAP = {
    'economy': 'economy',
    'eco': 'economy',
    'y': 'economy',
    'coach': 'economy',
    'premium economy': 'premium_economy',
    'premium': 'premium_economy',
    'premium eco': 'premium_economy',
    'w': 'premium_economy',
    'business': 'business',
    'biz': 'business',
    'j': 'business',
    'c': 'business',
    'first': 'first',
    'first class': 'first',
    'f': 'first',
}

# Maps vehicle type to emission factor activity type
VEHICLE_TYPE_MAP = {
    'small petrol': 'car_small_petrol',
    'small': 'car_small_petrol',
    'compact': 'car_small_petrol',
    'medium diesel': 'car_medium_diesel',
    'medium': 'car_medium_diesel',
    'sedan': 'car_medium_diesel',
    'large diesel': 'car_large_diesel',
    'large': 'car_large_diesel',
    'suv': 'car_large_diesel',
    'taxi': 'taxi',
}


class TravelParser(BaseParser):
    """Parser for TMC-style corporate travel CSV reports."""
    
    source_type = 'travel'
    
    def detect_headers(self, raw_headers) -> Dict[str, str]:
        """Map travel report headers to canonical names."""
        header_map = {}
        for header in raw_headers:
            cleaned = header.strip()
            if cleaned in TRAVEL_HEADER_MAP:
                header_map[cleaned] = TRAVEL_HEADER_MAP[cleaned]
            else:
                header_map[cleaned] = cleaned.lower().replace(' ', '_')
        return header_map
    
    def parse_row(self, row: Dict[str, str], row_number: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single travel report row.
        
        Routes to sub-parsers based on expense type:
        - Flight: IATA lookup → Haversine distance → haul classification → factor
        - Hotel: nights × per-night factor
        - Ground transport: distance × per-km factor
        """
        expense_type = row.get('expense_type', '').strip().lower()
        travel_category = EXPENSE_TYPE_MAP.get(expense_type)
        
        if not travel_category:
            # Try to infer from other fields
            if row.get('origin') and row.get('destination'):
                travel_category = 'flight'
            elif row.get('nights'):
                travel_category = 'hotel'
            elif row.get('vehicle_type') or row.get('distance_km'):
                travel_category = 'car'
            else:
                raise ValueError(f"Cannot determine travel type from expense type: {expense_type!r}")
        
        # Parse date
        date_str = row.get('transaction_date', '').strip()
        travel_date = parse_date_strict(date_str) if date_str else None
        
        if travel_category == 'flight':
            return self._parse_flight(row, travel_date, row_number)
        elif travel_category == 'hotel':
            return self._parse_hotel(row, travel_date, row_number)
        elif travel_category in ('car', 'taxi', 'rail'):
            return self._parse_ground(row, travel_date, travel_category, row_number)
        
        return None
    
    def _parse_flight(self, row, travel_date, row_number) -> Dict[str, Any]:
        """Parse flight row: look up airports, calculate distance, classify haul."""
        origin_code = row.get('origin', '').strip().upper()
        dest_code = row.get('destination', '').strip().upper()
        
        if not origin_code or not dest_code:
            raise ValueError(f"Flight missing origin/destination: {origin_code} → {dest_code}")
        
        # Look up airport coordinates
        try:
            origin = AirportLookup.objects.get(iata_code=origin_code)
            dest = AirportLookup.objects.get(iata_code=dest_code)
        except AirportLookup.DoesNotExist as e:
            raise ValueError(f"Unknown airport code: {e}")
        
        # Calculate distance with 9% DEFRA uplift
        one_way_km = calculate_flight_distance(
            float(origin.latitude), float(origin.longitude),
            float(dest.latitude), float(dest.longitude),
            apply_uplift=True
        )
        
        # Apply round-trip multiplier
        route_type = row.get('route_type', 'One Way').strip()
        multiplier = get_round_trip_multiplier(route_type)
        total_km = one_way_km * multiplier
        
        # Classify haul
        haul = classify_haul(float(one_way_km))
        
        # Get cabin class
        cabin_raw = row.get('cabin_class', 'economy').strip().lower()
        cabin = CABIN_CLASS_MAP.get(cabin_raw, 'economy')
        
        # Build activity type for emission factor lookup
        activity_type = f"flight_{haul}_{cabin}"
        
        return {
            'scope': 'scope_3',
            'scope_category': 'business_travel_cat6',
            'activity_type': activity_type,
            'quantity': total_km,
            'unit': 'pkm',
            'original_quantity': total_km,
            'original_unit': 'pkm',
            'period_start': travel_date,
            'period_end': travel_date,
            'facility_code': f"{origin_code}-{dest_code}",
            'facility_name': f"{origin.city} → {dest.city}",
            'region': None,
            '_origin': origin_code,
            '_destination': dest_code,
            '_haul': haul,
            '_cabin': cabin,
            '_route_type': route_type,
            '_distance_km': float(total_km),
        }
    
    def _parse_hotel(self, row, travel_date, row_number) -> Dict[str, Any]:
        """Parse hotel row: extract nights and location."""
        nights_str = row.get('nights', '').strip()
        if not nights_str:
            raise ValueError("Hotel record missing number of nights")
        
        nights = parse_number(nights_str)
        if nights <= 0:
            raise ValueError(f"Invalid hotel nights: {nights}")
        
        location = row.get('hotel_location', '').strip()
        
        return {
            'scope': 'scope_3',
            'scope_category': 'business_travel_cat6',
            'activity_type': 'hotel_night',
            'quantity': nights,
            'unit': 'night',
            'original_quantity': nights,
            'original_unit': 'night',
            'period_start': travel_date,
            'period_end': travel_date,
            'facility_code': '',
            'facility_name': location or 'Unknown hotel',
            'region': None,
            '_location': location,
        }
    
    def _parse_ground(self, row, travel_date, category, row_number) -> Dict[str, Any]:
        """Parse ground transport: car rental, taxi, rail."""
        # Get distance
        distance_str = row.get('distance_km', '').strip()
        distance_miles = row.get('distance_miles', '').strip()
        
        if distance_str:
            distance_km = parse_number(distance_str)
        elif distance_miles:
            distance_km = parse_number(distance_miles) * Decimal('1.60934')
        else:
            raise ValueError("Ground transport missing distance")
        
        # Determine vehicle type
        vehicle_raw = row.get('vehicle_type', '').strip().lower()
        vehicle_type = VEHICLE_TYPE_MAP.get(vehicle_raw)
        
        if not vehicle_type:
            if category == 'taxi':
                vehicle_type = 'taxi'
            else:
                vehicle_type = 'car_medium_diesel'  # Default
        
        return {
            'scope': 'scope_3',
            'scope_category': 'business_travel_cat6',
            'activity_type': vehicle_type,
            'quantity': distance_km,
            'unit': 'km',
            'original_quantity': distance_km,
            'original_unit': 'km',
            'period_start': travel_date,
            'period_end': travel_date,
            'facility_code': '',
            'facility_name': f"{category.title()} - {vehicle_raw or 'Unknown'}",
            'region': None,
            '_vehicle_type': vehicle_raw,
        }
    
    def _detect_flags(self, normalized, all_rows, row_num):
        """Travel-specific flag detection."""
        flags = super()._detect_flags(normalized, all_rows, row_num)
        
        activity = normalized.get('activity_type', '')
        
        # Flag unknown airport codes
        if 'flight' in activity:
            origin = normalized.get('_origin', '')
            dest = normalized.get('_destination', '')
            
            for code in [origin, dest]:
                if code and not AirportLookup.objects.filter(iata_code=code).exists():
                    flags.append({
                        'type': 'unknown_airport',
                        'severity': 'error',
                        'message': f"IATA code '{code}' not in airport lookup table",
                    })
        
        # Flag very long flights (> 18,000 km one-way — longer than any direct route)
        distance = normalized.get('_distance_km', 0)
        if distance > 36000:
            flags.append({
                'type': 'high_value',
                'severity': 'warning',
                'message': f"Flight distance of {distance:.0f} km seems excessive",
            })
        
        # Flag missing distance for ground transport
        if activity in ('car_medium_diesel', 'car_small_petrol', 'car_large_diesel', 'taxi'):
            if normalized.get('quantity', 0) == 0:
                flags.append({
                    'type': 'missing_distance',
                    'severity': 'error',
                    'message': 'Ground transport record has no distance',
                })
        
        return flags
