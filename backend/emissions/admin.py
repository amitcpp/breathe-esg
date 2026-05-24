"""Admin for emissions models."""
from django.contrib import admin
from emissions.models import EmissionRecord, EmissionFactor

@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'category', 'co2e_per_unit', 'unit', 'region', 'source_db']
    list_filter = ['category', 'source_db', 'region']
    search_fields = ['activity_type']

@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'scope', 'quantity', 'unit', 'co2e_kg', 'review_status', 'is_locked']
    list_filter = ['scope', 'review_status', 'is_locked', 'tenant']
    search_fields = ['activity_type', 'facility_name']
