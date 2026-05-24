"""
Base parser class for all source types.

Provides the common interface and shared logic for parsing uploaded CSV files,
creating RawRecords, and orchestrating the normalization pipeline.
"""
import csv
import hashlib
import io
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from django.utils import timezone

from ingestion.models import DataIngestion, RawRecord
from emissions.models import EmissionRecord, EmissionFactor
from review.models import AuditLog

logger = logging.getLogger(__name__)


class ParseError:
    """Structured parse error for a single row."""
    def __init__(self, row_number: int, field: str, message: str, severity: str = 'error'):
        self.row_number = row_number
        self.field = field
        self.message = message
        self.severity = severity

    def to_dict(self):
        return {
            'row': self.row_number,
            'field': self.field,
            'message': self.message,
            'severity': self.severity,
        }


class BaseParser:
    """
    Abstract base class for source-specific parsers.
    
    Subclasses must implement:
    - detect_headers(): Map raw CSV headers to canonical field names
    - parse_row(): Convert a single raw row dict into normalized data
    - get_scope(): Return the GHG scope for this source
    - get_scope_category(): Return the scope sub-category
    """
    
    # Subclasses set this
    source_type: str = None
    
    def __init__(self, tenant, user):
        self.tenant = tenant
        self.user = user
        self.errors: List[ParseError] = []
        self.warnings: List[ParseError] = []
    
    def process_file(self, file_content: bytes, file_name: str) -> DataIngestion:
        """
        Main entry point: process an uploaded file end-to-end.
        
        1. Create DataIngestion record
        2. Detect CSV dialect and headers
        3. Parse each row into RawRecord + EmissionRecord
        4. Update ingestion status
        """
        # Compute file hash for dedup
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Create ingestion record
        ingestion = DataIngestion.objects.create(
            tenant=self.tenant,
            source_type=self.source_type,
            file_name=file_name,
            file_hash=file_hash,
            uploaded_by=self.user,
            status='processing',
        )
        
        try:
            # Decode file content
            text = self._decode_file(file_content)
            
            # Detect delimiter and parse CSV
            rows = self._parse_csv(text)
            
            if not rows:
                ingestion.status = 'failed'
                ingestion.processing_log = [{'error': 'No data rows found in file'}]
                ingestion.save()
                return ingestion
            
            # Detect and map headers
            header_map = self.detect_headers(rows[0].keys())
            
            success_count = 0
            error_count = 0
            log_entries = []
            
            for i, row in enumerate(rows, start=1):
                # Create raw record (always, even if parsing fails)
                raw_record = RawRecord.objects.create(
                    ingestion=ingestion,
                    tenant=self.tenant,
                    row_number=i,
                    raw_data=row,
                )
                
                try:
                    # Map headers and parse row
                    mapped_row = self._apply_header_map(row, header_map)
                    normalized = self.parse_row(mapped_row, i)
                    
                    if normalized is None:
                        raw_record.parse_status = 'skipped'
                        raw_record.parse_errors = [{'message': 'Row skipped by parser'}]
                        raw_record.save()
                        continue
                    
                    # Look up emission factor
                    emission_factor = self._find_emission_factor(normalized)
                    
                    # Calculate CO2e
                    co2e = self._calculate_co2e(normalized, emission_factor)
                    
                    # Detect flags
                    flags = self._detect_flags(normalized, rows, i)
                    
                    # Set review status based on flags
                    review_status = 'pending'
                    if any(f['severity'] == 'error' for f in flags):
                        review_status = 'flagged'
                    
                    # Create emission record
                    emission_record = EmissionRecord.objects.create(
                        tenant=self.tenant,
                        raw_record=raw_record,
                        ingestion=ingestion,
                        scope=normalized['scope'],
                        scope_category=normalized['scope_category'],
                        activity_type=normalized['activity_type'],
                        quantity=normalized['quantity'],
                        unit=normalized['unit'],
                        original_quantity=normalized['original_quantity'],
                        original_unit=normalized['original_unit'],
                        period_start=normalized['period_start'],
                        period_end=normalized.get('period_end'),
                        facility_code=normalized.get('facility_code', ''),
                        facility_name=normalized.get('facility_name', ''),
                        emission_factor=emission_factor,
                        co2e_kg=co2e,
                        review_status=review_status,
                        flags=flags,
                    )
                    
                    # Create audit log
                    AuditLog.objects.create(
                        tenant=self.tenant,
                        emission_record=emission_record,
                        action='created',
                        performed_by=self.user,
                        metadata={
                            'ingestion_id': str(ingestion.id),
                            'source_file': file_name,
                            'row_number': i,
                        }
                    )
                    
                    raw_record.parse_status = 'parsed'
                    raw_record.save()
                    success_count += 1
                    
                except Exception as e:
                    raw_record.parse_status = 'failed'
                    raw_record.parse_errors = [{'message': str(e)}]
                    raw_record.save()
                    error_count += 1
                    log_entries.append({
                        'row': i,
                        'error': str(e),
                        'severity': 'error',
                    })
                    logger.warning(f"Row {i} parse error: {e}")
            
            # Update ingestion status
            ingestion.row_count = len(rows)
            ingestion.success_count = success_count
            ingestion.error_count = error_count
            ingestion.processing_log = log_entries
            
            if error_count == 0:
                ingestion.status = 'completed'
            elif success_count > 0:
                ingestion.status = 'completed_with_errors'
            else:
                ingestion.status = 'failed'
            
            ingestion.save()
            return ingestion
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            ingestion.status = 'failed'
            ingestion.processing_log = [{'error': str(e), 'severity': 'critical'}]
            ingestion.save()
            return ingestion
    
    def _decode_file(self, content: bytes) -> str:
        """Try UTF-8, then Latin-1 (common for SAP exports)."""
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode file with any supported encoding")
    
    def _parse_csv(self, text: str) -> List[Dict[str, str]]:
        """
        Parse CSV text, auto-detecting delimiter (comma, semicolon, tab, pipe).
        Skips metadata header rows that some exports prepend.
        """
        # Try to detect delimiter
        first_lines = text.split('\n', 5)
        delimiter = self._detect_delimiter(first_lines)
        
        # Find the actual header row (skip metadata lines)
        lines = text.strip().split('\n')
        header_line_idx = self._find_header_line(lines, delimiter)
        
        if header_line_idx is None:
            header_line_idx = 0
        
        # Parse from header line onwards
        data_text = '\n'.join(lines[header_line_idx:])
        reader = csv.DictReader(io.StringIO(data_text), delimiter=delimiter)
        
        rows = []
        for row in reader:
            # Skip completely empty rows
            if all(v is None or v.strip() == '' for v in row.values()):
                continue
            # Clean keys and values
            cleaned = {}
            for k, v in row.items():
                if k is not None:
                    cleaned[k.strip()] = v.strip() if v else ''
            rows.append(cleaned)
        
        return rows
    
    def _detect_delimiter(self, lines: List[str]) -> str:
        """Auto-detect CSV delimiter by counting occurrences."""
        delimiters = {';': 0, ',': 0, '\t': 0, '|': 0}
        
        for line in lines:
            for d in delimiters:
                delimiters[d] += line.count(d)
        
        # Return the most frequent delimiter, defaulting to comma
        best = max(delimiters, key=delimiters.get)
        if delimiters[best] == 0:
            return ','
        return best
    
    def _find_header_line(self, lines: List[str], delimiter: str) -> Optional[int]:
        """
        Find the actual header row, skipping metadata rows.
        Heuristic: header row has more delimiters and mostly text values.
        """
        if len(lines) <= 1:
            return 0
        
        # Count delimiters per line - header usually has similar count to data
        counts = [(i, line.count(delimiter)) for i, line in enumerate(lines[:10])]
        
        if not counts:
            return 0
        
        # Find the first line with a high delimiter count
        max_count = max(c for _, c in counts)
        if max_count == 0:
            return 0
        
        for i, count in counts:
            if count >= max_count * 0.7:  # Within 70% of max
                return i
        
        return 0
    
    def _apply_header_map(self, row: Dict[str, str], header_map: Dict[str, str]) -> Dict[str, str]:
        """Map raw column names to canonical field names."""
        mapped = {}
        for raw_key, value in row.items():
            canonical = header_map.get(raw_key, raw_key)
            mapped[canonical] = value
        # Also keep original keys for raw_data
        return mapped
    
    def _find_emission_factor(self, normalized: Dict[str, Any]) -> Optional[EmissionFactor]:
        """Look up the appropriate emission factor for this activity."""
        activity_type = normalized.get('activity_type', '')
        region = normalized.get('region')
        
        query = EmissionFactor.objects.filter(activity_type=activity_type)
        
        if region:
            # Try region-specific first, then generic
            regional = query.filter(region=region).first()
            if regional:
                return regional
        
        return query.first()
    
    def _calculate_co2e(self, normalized: Dict[str, Any], factor: Optional[EmissionFactor]) -> Decimal:
        """Calculate CO₂e using the emission factor."""
        if factor is None:
            return Decimal('0')
        
        quantity = normalized.get('quantity', Decimal('0'))
        return (quantity * factor.co2e_per_unit).quantize(Decimal('0.0001'))
    
    def _detect_flags(self, normalized: Dict[str, Any], all_rows: list, row_num: int) -> list:
        """Base flag detection. Subclasses add source-specific flags."""
        flags = []
        
        # Negative value check
        if normalized.get('quantity', 0) < 0:
            flags.append({
                'type': 'negative_value',
                'severity': 'error',
                'message': f"Negative quantity: {normalized['quantity']}",
            })
        
        # Zero value check
        if normalized.get('quantity', 0) == 0:
            flags.append({
                'type': 'zero_value',
                'severity': 'warning',
                'message': 'Quantity is zero',
            })
        
        return flags
    
    # Abstract methods for subclasses
    def detect_headers(self, raw_headers) -> Dict[str, str]:
        raise NotImplementedError
    
    def parse_row(self, row: Dict[str, str], row_number: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
