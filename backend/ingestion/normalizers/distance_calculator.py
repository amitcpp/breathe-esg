"""
Great-circle distance calculator using the Haversine formula.

Used by the travel parser to calculate flight distances from IATA airport
codes when the source data doesn't provide distance directly (which is
the common case with Concur/Navan exports).

The Haversine formula gives the shortest distance between two points on
Earth's surface. DEFRA recommends applying a 9% uplift factor to account
for indirect routing, holding patterns, and air traffic control.
"""
import math
from decimal import Decimal
from typing import Optional, Tuple

# Earth's mean radius in kilometers
EARTH_RADIUS_KM = 6371.0

# DEFRA-recommended uplift factor for flight distance
FLIGHT_UPLIFT_FACTOR = 1.09

# Haul category thresholds (in km)
SHORT_HAUL_THRESHOLD = 3700  # < 3700 km = short-haul per DEFRA


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.
    
    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees)
        lat2, lon2: Latitude and longitude of point 2 (in degrees)
    
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return EARTH_RADIUS_KM * c


def calculate_flight_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    apply_uplift: bool = True
) -> Decimal:
    """
    Calculate flight distance with optional DEFRA 9% uplift.
    
    Returns distance in km as Decimal for precision.
    """
    gcd = haversine_distance(lat1, lon1, lat2, lon2)
    
    if apply_uplift:
        gcd *= FLIGHT_UPLIFT_FACTOR
    
    return Decimal(str(round(gcd, 2)))


def classify_haul(distance_km: float) -> str:
    """
    Classify flight as short-haul or long-haul based on DEFRA thresholds.
    
    DEFRA uses 3,700 km as the boundary:
    - < 3,700 km → short-haul
    - ≥ 3,700 km → long-haul
    """
    if distance_km < SHORT_HAUL_THRESHOLD:
        return 'short_haul'
    return 'long_haul'


def get_round_trip_multiplier(route_type: str) -> int:
    """
    Determine the distance multiplier based on route type.
    Round trips are 2x the one-way distance.
    """
    route_lower = route_type.strip().lower() if route_type else ''
    if route_lower in ('round trip', 'roundtrip', 'round_trip', 'return', 'rt'):
        return 2
    return 1
