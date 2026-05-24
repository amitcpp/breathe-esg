"""Admin for ingestion models."""
from django.contrib import admin
from ingestion.models import DataIngestion, RawRecord

@admin.register(DataIngestion)
class DataIngestionAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'source_type', 'status', 'row_count', 'success_count', 'error_count', 'uploaded_at']
    list_filter = ['source_type', 'status', 'tenant']

@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ['row_number', 'parse_status', 'ingestion', 'created_at']
    list_filter = ['parse_status']
