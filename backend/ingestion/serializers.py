"""Ingestion serializers."""
from rest_framework import serializers
from ingestion.models import DataIngestion, RawRecord


class DataIngestionSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True, default='')

    class Meta:
        model = DataIngestion
        fields = [
            'id', 'source_type', 'source_type_display', 'file_name', 'file_hash',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'status',
            'row_count', 'success_count', 'error_count', 'processing_log',
        ]
        read_only_fields = fields


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ['id', 'row_number', 'raw_data', 'parse_status', 'parse_errors', 'created_at']
        read_only_fields = fields


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    source_type = serializers.ChoiceField(choices=[
        ('sap_fuel', 'SAP Fuel & Procurement'),
        ('utility_electricity', 'Utility Electricity'),
        ('travel', 'Corporate Travel'),
    ])
