"""
Utility Electricity Parser (Scope 2).

Handles CSV exports from utility portals (Green Button-style).
Real utility data quirks handled:
- Non-calendar billing periods (28-35 days, e.g., Jan 12 – Feb 10)
- Estimated vs. actual read flags
- Meter multiplier (CT ratio for commercial meters)
- Multiple meters per facility
- Various date formats (MM/DD/YYYY, YYYY-MM-DD)
- Demand (kW) stored separately from consumption (kWh)
"""
from decimal import Decimal
from typing import Dict, Any, Optional

from ingestion.parsers.base import BaseParser
from ingestion.normalizers.unit_converter import parse_number, convert_to_canonical
from ingestion.normalizers.date_normalizer import parse_date, parse_date_strict


# Maps common utility CSV column headers to canonical names
UTILITY_HEADER_MAP = {
    # Account
    'Account Number': 'account_number',
    'Account': 'account_number',
    'Account No': 'account_number',
    'Account #': 'account_number',
    'Service Agreement': 'account_number',
    # Meter
    'Meter ID': 'meter_id',
    'Meter Number': 'meter_id',
    'Meter No': 'meter_id',
    'Meter': 'meter_id',
    'Service ID': 'meter_id',
    # Address
    'Service Address': 'service_address',
    'Address': 'service_address',
    'Location': 'service_address',
    'Facility': 'service_address',
    # Dates
    'Start Date': 'start_date',
    'Bill Start': 'start_date',
    'Period Start': 'start_date',
    'From Date': 'start_date',
    'From': 'start_date',
    'End Date': 'end_date',
    'Bill End': 'end_date',
    'Period End': 'end_date',
    'To Date': 'end_date',
    'To': 'end_date',
    'Date': 'start_date',
    # Usage
    'Usage (kWh)': 'usage_kwh',
    'Usage': 'usage_kwh',
    'kWh': 'usage_kwh',
    'Consumption': 'usage_kwh',
    'Consumption (kWh)': 'usage_kwh',
    'Energy (kWh)': 'usage_kwh',
    'Total Usage': 'usage_kwh',
    'Total kWh': 'usage_kwh',
    # Demand
    'Demand (kW)': 'demand_kw',
    'Demand': 'demand_kw',
    'Peak Demand': 'demand_kw',
    'Peak Demand (kW)': 'demand_kw',
    'kW': 'demand_kw',
    # Read type
    'Read Type': 'read_type',
    'Type': 'read_type',
    'Reading Type': 'read_type',
    'Estimated': 'read_type',
    # Rate
    'Rate Schedule': 'rate_schedule',
    'Rate': 'rate_schedule',
    'Tariff': 'rate_schedule',
    # Cost
    'Cost ($)': 'cost',
    'Cost': 'cost',
    'Amount': 'cost',
    'Total Cost': 'cost',
    'Charges': 'cost',
    'Total Charges': 'cost',
    # Units
    'Units': 'units',
    'Unit': 'units',
    'UOM': 'units',
    # Meter multiplier
    'Meter Multiplier': 'meter_multiplier',
    'Multiplier': 'meter_multiplier',
    'CT Ratio': 'meter_multiplier',
}


class UtilityParser(BaseParser):
    """Parser for utility portal CSV electricity exports."""
    
    source_type = 'utility_electricity'
    
    def detect_headers(self, raw_headers) -> Dict[str, str]:
        """Map utility CSV headers to canonical names."""
        header_map = {}
        for header in raw_headers:
            cleaned = header.strip()
            if cleaned in UTILITY_HEADER_MAP:
                header_map[cleaned] = UTILITY_HEADER_MAP[cleaned]
            else:
                header_map[cleaned] = cleaned.lower().replace(' ', '_').replace('(', '').replace(')', '')
        return header_map
    
    def parse_row(self, row: Dict[str, str], row_number: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single utility data row into normalized emission data.
        
        Key transformations:
        1. Parse billing period dates
        2. Parse consumption with meter multiplier
        3. Normalize to kWh
        4. Flag estimated reads
        """
        # Parse consumption
        usage_str = row.get('usage_kwh', '').strip()
        if not usage_str:
            return None
        
        usage = parse_number(usage_str)
        
        # Apply meter multiplier if present
        multiplier_str = row.get('meter_multiplier', '').strip()
        if multiplier_str:
            try:
                multiplier = parse_number(multiplier_str)
                usage = usage * multiplier
            except (ValueError, TypeError):
                pass
        
        # Determine unit
        raw_unit = row.get('units', 'kWh').strip() or 'kWh'
        normalized_qty, normalized_unit = convert_to_canonical(usage, raw_unit, 'kWh')
        
        # Parse dates
        start_str = row.get('start_date', '').strip()
        end_str = row.get('end_date', '').strip()
        
        start_date = parse_date_strict(start_str) if start_str else None
        end_date = parse_date(end_str) if end_str else None
        
        if start_date is None:
            raise ValueError(f"Missing or unparseable start date: {start_str!r}")
        
        # Determine read type
        read_type = row.get('read_type', 'Actual').strip().lower()
        is_estimated = read_type in ('estimated', 'est', 'e', 'yes', 'true')
        
        # Build meter/facility identifier
        meter_id = row.get('meter_id', '').strip()
        account = row.get('account_number', '').strip()
        address = row.get('service_address', '').strip()
        
        facility_code = meter_id or account
        facility_name = address or f"Meter {meter_id}"
        
        return {
            'scope': 'scope_2',
            'scope_category': 'purchased_electricity',
            'activity_type': 'grid_electricity',
            'quantity': normalized_qty,
            'unit': normalized_unit,
            'original_quantity': usage,
            'original_unit': raw_unit,
            'period_start': start_date,
            'period_end': end_date,
            'facility_code': facility_code,
            'facility_name': facility_name,
            'region': None,  # Would need mapping from address to grid region
            # Context for flags
            '_is_estimated': is_estimated,
            '_read_type': read_type,
            '_demand_kw': row.get('demand_kw', ''),
            '_billing_days': (end_date - start_date).days if end_date and start_date else None,
        }
    
    def _detect_flags(self, normalized, all_rows, row_num):
        """Utility-specific flag detection."""
        flags = super()._detect_flags(normalized, all_rows, row_num)
        
        # Flag estimated reads
        if normalized.get('_is_estimated'):
            flags.append({
                'type': 'estimated_read',
                'severity': 'info',
                'message': 'Meter reading is estimated, not actual',
            })
        
        # Flag unusual billing period length
        billing_days = normalized.get('_billing_days')
        if billing_days is not None:
            if billing_days < 20:
                flags.append({
                    'type': 'short_billing_period',
                    'severity': 'warning',
                    'message': f'Billing period is only {billing_days} days — unusually short',
                })
            elif billing_days > 40:
                flags.append({
                    'type': 'long_billing_period',
                    'severity': 'warning',
                    'message': f'Billing period is {billing_days} days — unusually long',
                })
        
        # Flag very high daily consumption (> 1000 kWh/day for single meter)
        if billing_days and billing_days > 0:
            daily_usage = float(normalized.get('quantity', 0)) / billing_days
            if daily_usage > 5000:
                flags.append({
                    'type': 'high_value',
                    'severity': 'warning',
                    'message': f'Daily usage of {daily_usage:.0f} kWh/day seems high — verify meter multiplier',
                })
        
        return flags
