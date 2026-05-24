"""
Emissions models: EmissionRecord and EmissionFactor.

EmissionRecord is the core normalized row — the single representation of an
emission-producing activity after ingestion, normalization, and factor application.
It tracks both the original and normalized values, the emission factor used,
and the review/audit lifecycle.

EmissionFactor is the reference table of DEFRA/EPA/custom factors used to
convert activity data into CO₂e.
"""
import uuid
from django.db import models
from core.models import Tenant, User


class EmissionFactor(models.Model):
    """
    Reference emission factor from DEFRA, EPA, or custom source.
    
    Each factor converts one unit of activity (e.g., 1 liter of diesel,
    1 kWh of electricity, 1 passenger-km of flight) into kg CO₂e.
    
    Factors are versioned by valid_from/valid_to dates to support
    year-over-year reporting with the correct factor vintage.
    """
    CATEGORY_CHOICES = [
        ('fuel', 'Fuel Combustion'),
        ('electricity', 'Grid Electricity'),
        ('travel_air', 'Air Travel'),
        ('travel_hotel', 'Hotel Stay'),
        ('travel_car', 'Car / Ground Transport'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_db = models.CharField(
        max_length=50,
        help_text="Factor database, e.g. DEFRA_2024, EPA_2024, custom"
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    activity_type = models.CharField(
        max_length=100,
        help_text="e.g. diesel, petrol, natural_gas, grid_electricity, short_haul_economy"
    )
    sub_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Further classification, e.g. with_rf, without_rf"
    )
    unit = models.CharField(
        max_length=30,
        help_text="Factor is per this unit: L, kWh, pkm, night, km"
    )
    co2e_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        help_text="kg CO₂e per unit (total GHG impact)"
    )
    co2_per_unit = models.DecimalField(
        max_digits=12, decimal_places=8, null=True, blank=True,
        help_text="kg CO₂ per unit (CO₂ only)"
    )
    ch4_per_unit = models.DecimalField(
        max_digits=12, decimal_places=8, null=True, blank=True,
        help_text="kg CH₄ per unit"
    )
    n2o_per_unit = models.DecimalField(
        max_digits=12, decimal_places=8, null=True, blank=True,
        help_text="kg N₂O per unit"
    )
    valid_from = models.DateField(help_text="Factor valid from this date")
    valid_to = models.DateField(null=True, blank=True, help_text="Factor valid until (null = current)")
    region = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Applicable region/country, e.g. UK, US, IN, DE"
    )

    class Meta:
        ordering = ['category', 'activity_type']
        indexes = [
            models.Index(fields=['category', 'activity_type']),
            models.Index(fields=['region']),
        ]

    def __str__(self):
        region_str = f" ({self.region})" if self.region else ""
        return f"{self.activity_type}{region_str}: {self.co2e_per_unit} kgCO₂e/{self.unit}"


class EmissionRecord(models.Model):
    """
    The core normalized emission record.
    
    This is where raw source data converges into a single schema regardless
    of origin (SAP, utility, or travel). Each record represents one
    emission-producing activity with:
    
    - GHG scope categorization (1, 2, or 3)
    - Normalized activity data (quantity + unit)
    - Original activity data (preserved for audit)
    - Applied emission factor and calculated CO₂e
    - Review state machine (pending → approved/rejected → locked)
    - Auto-detected anomaly flags
    - Full provenance back to raw source
    """
    SCOPE_CHOICES = [
        ('scope_1', 'Scope 1 - Direct Emissions'),
        ('scope_2', 'Scope 2 - Indirect Energy'),
        ('scope_3', 'Scope 3 - Value Chain'),
    ]

    REVIEW_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged for Review'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')

    # Source-of-truth linkage
    raw_record = models.OneToOneField(
        'ingestion.RawRecord',
        on_delete=models.CASCADE,
        related_name='emission_record',
        help_text="Link to the original raw source row"
    )
    ingestion = models.ForeignKey(
        'ingestion.DataIngestion',
        on_delete=models.CASCADE,
        related_name='emission_records',
        help_text="Which upload produced this record"
    )

    # GHG categorization
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    scope_category = models.CharField(
        max_length=100,
        help_text="e.g. stationary_combustion, purchased_electricity, business_travel_cat6"
    )
    activity_type = models.CharField(
        max_length=100,
        help_text="e.g. diesel_combustion, grid_electricity, flight_short_haul_economy"
    )

    # Normalized activity data
    quantity = models.DecimalField(
        max_digits=16, decimal_places=6,
        help_text="Quantity in normalized unit"
    )
    unit = models.CharField(
        max_length=20,
        help_text="Normalized unit: L, kWh, pkm, night, km"
    )

    # Original activity data (preserved for audit)
    original_quantity = models.DecimalField(
        max_digits=16, decimal_places=6,
        help_text="Quantity as received from source"
    )
    original_unit = models.CharField(
        max_length=30,
        help_text="Unit as received from source"
    )

    # Time period
    period_start = models.DateField(help_text="Activity period start")
    period_end = models.DateField(
        null=True, blank=True,
        help_text="Activity period end (null for point-in-time events)"
    )

    # Location / entity
    facility_code = models.CharField(
        max_length=50, blank=True,
        help_text="Plant code, meter ID, or similar identifier"
    )
    facility_name = models.CharField(max_length=255, blank=True)

    # Emission calculation
    emission_factor = models.ForeignKey(
        EmissionFactor,
        on_delete=models.PROTECT,  # Don't allow deleting factors with linked records
        related_name='emission_records',
        null=True,
        blank=True,
    )
    co2e_kg = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="Calculated kg CO₂e = quantity × emission_factor"
    )

    # Review workflow
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='pending'
    )
    flags = models.JSONField(
        default=list,
        blank=True,
        help_text="Auto-detected anomaly flags, e.g. [{type: 'high_value', severity: 'warning', message: '...'}]"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, help_text="Analyst comments on this record")

    # Audit lock
    is_locked = models.BooleanField(
        default=False,
        help_text="True after audit approval — record becomes immutable"
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='locked_records'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(
        default=1,
        help_text="Incremented on each edit for optimistic concurrency"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'scope']),
            models.Index(fields=['tenant', 'review_status']),
            models.Index(fields=['tenant', 'ingestion']),
            models.Index(fields=['scope', 'activity_type']),
            models.Index(fields=['review_status']),
            models.Index(fields=['is_locked']),
        ]

    def __str__(self):
        return f"{self.get_scope_display()} | {self.activity_type} | {self.co2e_kg} kgCO₂e"
