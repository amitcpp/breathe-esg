"""Admin for reference models."""
from django.contrib import admin
from reference.models import PlantCodeLookup, AirportLookup

@admin.register(PlantCodeLookup)
class PlantCodeAdmin(admin.ModelAdmin):
    list_display = ['plant_code', 'facility_name', 'country', 'tenant']
    list_filter = ['tenant', 'country']

@admin.register(AirportLookup)
class AirportAdmin(admin.ModelAdmin):
    list_display = ['iata_code', 'name', 'city', 'country']
    search_fields = ['iata_code', 'name', 'city']
