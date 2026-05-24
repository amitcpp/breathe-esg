"""
Reference models: PlantCodeLookup and AirportLookup.

These are tenant-specific (plant codes) and global (airports) reference
tables that the parsers use during normalization.
"""
from django.db import models
from core.models import Tenant


class PlantCodeLookup(models.Model):
    """
    Maps SAP plant codes to human-readable facility names.
    
    SAP plant codes (Werk) are 4-character identifiers that mean nothing
    without context. Each tenant configures their own mapping since plant
    codes are organization-specific.
    """
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='plant_codes')
    plant_code = models.CharField(max_length=10, help_text="SAP Werk code, e.g. 1000")
    facility_name = models.CharField(max_length=255, help_text="Human-readable facility name")
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2 country code")
    region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Region for grid emission factor lookup"
    )

    class Meta:
        unique_together = ['tenant', 'plant_code']
        ordering = ['tenant', 'plant_code']

    def __str__(self):
        return f"{self.plant_code} → {self.facility_name}"


class AirportLookup(models.Model):
    """
    IATA airport codes with coordinates for distance calculation.
    
    Used by the travel parser to calculate great-circle distance
    between origin and destination airports using the Haversine formula.
    Global reference data (not tenant-specific).
    """
    iata_code = models.CharField(max_length=3, primary_key=True, help_text="IATA 3-letter code")
    name = models.CharField(max_length=255, help_text="Airport name")
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)

    class Meta:
        ordering = ['iata_code']

    def __str__(self):
        return f"{self.iata_code} - {self.name} ({self.city})"
