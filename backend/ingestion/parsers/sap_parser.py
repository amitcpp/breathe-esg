"""
SAP Fuel & Procurement Parser (Scope 1).

Handles CSV exports from SAP ME2M (Purchase Order List) transaction.
Real SAP quirks handled:
- German column headers (Materialnummer, Werk, Menge, etc.)
- Semicolon delimiter (German CSV standard since comma = decimal)
- DD.MM.YYYY date format
- German number format (1.234,56)
- Inconsistent UoM codes (L, LTR, Liter, l)
- Plant codes requiring lookup table
- Material groups for fuel type identification
"""
from decimal import Decimal
from typing import Dict, Any, Optional

from ingestion.parsers.base import BaseParser
from ingestion.normalizers.unit_converter import parse_german_decimal, convert_to_canonical, normalize_unit
from ingestion.normalizers.date_normalizer import parse_date_strict
from reference.models import PlantCodeLookup

# Maps German (and English) SAP column headers to canonical field names
SAP_HEADER_MAP = {
    # German headers
    'Einkaufsbeleg': 'purchase_order',
    'Bestellnummer': 'purchase_order',
    'Pos': 'item_number',
    'Position': 'item_number',
    'Materialnr': 'material_number',
    'Materialnummer': 'material_number',
    'Kurztext': 'description',
    'Werk': 'plant_code',
    'Menge': 'quantity',
    'Bestellmenge': 'quantity',
    'ME': 'unit',
    'Mengeneinheit': 'unit',
    'Bestelldatum': 'document_date',
    'Belegdatum': 'document_date',
    'Buchungsdatum': 'posting_date',
    'Warengruppe': 'material_group',
    'Nettopreis': 'net_price',
    'Währ': 'currency',
    'Währung': 'currency',
    'Lieferant': 'vendor',
    'Buchungskreis': 'company_code',
    'Lagerort': 'storage_location',
    'Bewegungsart': 'movement_type',
    # English headers
    'Purchase Order': 'purchase_order',
    'Item': 'item_number',
    'Material': 'material_number',
    'Material Number': 'material_number',
    'Short Text': 'description',
    'Description': 'description',
    'Plant': 'plant_code',
    'Quantity': 'quantity',
    'Order Quantity': 'quantity',
    'UoM': 'unit',
    'Unit': 'unit',
    'Unit of Measure': 'unit',
    'Document Date': 'document_date',
    'Posting Date': 'posting_date',
    'Material Group': 'material_group',
    'Net Price': 'net_price',
    'Currency': 'currency',
    'Vendor': 'vendor',
    'Company Code': 'company_code',
    'Storage Location': 'storage_location',
    'Movement Type': 'movement_type',
}

# Maps material group codes to fuel types (activity_type)
FUEL_TYPE_MAP = {
    'FUEL-DSL': 'diesel',
    'FUEL-01': 'diesel',
    'FUEL-GAS': 'petrol',
    'FUEL-02': 'petrol',
    'FUEL-PET': 'petrol',
    'FUEL-LPG': 'lpg',
    'FUEL-03': 'lpg',
    'FUEL-CNG': 'natural_gas',
    'FUEL-04': 'natural_gas',
    'FUEL-NG': 'natural_gas',
    'FUEL-HFO': 'heavy_fuel_oil',
    'FUEL-05': 'heavy_fuel_oil',
}

# Target units for each fuel type (match DEFRA factor units)
FUEL_TARGET_UNIT = {
    'diesel': 'L',
    'petrol': 'L',
    'lpg': 'L',
    'heavy_fuel_oil': 'L',
    'natural_gas': 'kWh',  # Natural gas uses energy-based factor
}


class SAPParser(BaseParser):
    """Parser for SAP ME2M fuel/procurement CSV exports."""
    
    source_type = 'sap_fuel'
    
    def detect_headers(self, raw_headers) -> Dict[str, str]:
        """Map raw SAP headers (possibly German) to canonical names."""
        header_map = {}
        for header in raw_headers:
            cleaned = header.strip()
            if cleaned in SAP_HEADER_MAP:
                header_map[cleaned] = SAP_HEADER_MAP[cleaned]
            else:
                header_map[cleaned] = cleaned.lower().replace(' ', '_')
        return header_map
    
    def parse_row(self, row: Dict[str, str], row_number: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single SAP export row into normalized emission data.
        
        Key transformations:
        1. Parse German-format numbers (1.234,56)
        2. Parse DD.MM.YYYY dates
        3. Map material group → fuel type
        4. Look up plant code → facility name
        5. Normalize unit to DEFRA-compatible (Liters for liquid fuel, kWh for gas)
        """
        # Skip rows without quantity
        qty_str = row.get('quantity', '').strip()
        if not qty_str:
            return None
        
        # Parse quantity (German decimal format)
        quantity = parse_german_decimal(qty_str)
        if quantity <= 0:
            return None
        
        # Parse date
        date_str = row.get('document_date', '') or row.get('posting_date', '')
        doc_date = parse_date_strict(date_str)
        
        # Get unit and normalize
        raw_unit = row.get('unit', 'L').strip()
        
        # Determine fuel type from material group
        material_group = row.get('material_group', '').strip().upper()
        description = row.get('description', '').strip().lower()
        
        fuel_type = FUEL_TYPE_MAP.get(material_group)
        
        # Fallback: try to infer fuel type from description
        if not fuel_type:
            if any(w in description for w in ['diesel', 'en590', 'hsd', 'gasoil']):
                fuel_type = 'diesel'
            elif any(w in description for w in ['petrol', 'gasoline', 'benzin', 'mogas']):
                fuel_type = 'petrol'
            elif any(w in description for w in ['lpg', 'propane', 'butane']):
                fuel_type = 'lpg'
            elif any(w in description for w in ['natural gas', 'cng', 'lng', 'erdgas']):
                fuel_type = 'natural_gas'
            elif any(w in description for w in ['hfo', 'heavy fuel', 'bunker', 'fuel oil']):
                fuel_type = 'heavy_fuel_oil'
            else:
                fuel_type = 'diesel'  # Default assumption
        
        # Convert quantity to target unit for emission factor
        target_unit = FUEL_TARGET_UNIT.get(fuel_type, 'L')
        normalized_qty, normalized_unit = convert_to_canonical(quantity, raw_unit, target_unit)
        
        # Look up plant code
        plant_code = row.get('plant_code', '').strip()
        facility_name = ''
        region = None
        
        try:
            plant = PlantCodeLookup.objects.get(
                tenant=self.tenant,
                plant_code=plant_code
            )
            facility_name = plant.facility_name
            region = plant.region
        except PlantCodeLookup.DoesNotExist:
            pass
        
        return {
            'scope': 'scope_1',
            'scope_category': 'stationary_combustion',
            'activity_type': fuel_type,
            'quantity': normalized_qty,
            'unit': normalized_unit,
            'original_quantity': quantity,
            'original_unit': raw_unit,
            'period_start': doc_date,
            'period_end': doc_date,
            'facility_code': plant_code,
            'facility_name': facility_name,
            'region': region,
            # Extra context for flag detection
            '_purchase_order': row.get('purchase_order', ''),
            '_material_group': material_group,
            '_description': row.get('description', ''),
        }
    
    def _detect_flags(self, normalized, all_rows, row_num):
        """SAP-specific flag detection."""
        flags = super()._detect_flags(normalized, all_rows, row_num)
        
        # Flag unknown plant code
        if normalized.get('facility_code') and not normalized.get('facility_name'):
            flags.append({
                'type': 'unknown_plant',
                'severity': 'warning',
                'message': f"Plant code '{normalized['facility_code']}' not found in lookup table",
            })
        
        # Flag unknown material group
        if normalized.get('_material_group') and normalized['_material_group'] not in FUEL_TYPE_MAP:
            flags.append({
                'type': 'unknown_material_group',
                'severity': 'warning',
                'message': f"Material group '{normalized['_material_group']}' not in fuel type mapping — inferred from description",
            })
        
        # Flag very large quantities (> 50,000 liters in single PO line)
        if normalized.get('quantity', 0) > 50000 and normalized.get('unit') == 'L':
            flags.append({
                'type': 'high_value',
                'severity': 'warning',
                'message': f"Large fuel quantity: {normalized['quantity']}L — verify this is a single delivery",
            })
        
        return flags
