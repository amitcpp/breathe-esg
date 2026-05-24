"""Emissions serializers."""
from rest_framework import serializers
from emissions.models import EmissionRecord, EmissionFactor
from ingestion.serializers import RawRecordSerializer


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = [
            'id', 'source_db', 'category', 'activity_type', 'sub_type',
            'unit', 'co2e_per_unit', 'region', 'valid_from', 'valid_to',
        ]


class EmissionRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view."""
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)
    source_type = serializers.CharField(source='ingestion.source_type', read_only=True)
    source_file = serializers.CharField(source='ingestion.file_name', read_only=True)
    flag_count = serializers.SerializerMethodField()
    has_errors = serializers.SerializerMethodField()

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'scope', 'scope_display', 'scope_category', 'activity_type',
            'quantity', 'unit', 'original_quantity', 'original_unit',
            'period_start', 'period_end', 'facility_code', 'facility_name',
            'co2e_kg', 'review_status', 'review_status_display',
            'is_locked', 'flags', 'flag_count', 'has_errors',
            'source_type', 'source_file', 'created_at',
        ]

    def get_flag_count(self, obj):
        return len(obj.flags) if obj.flags else 0

    def get_has_errors(self, obj):
        if not obj.flags:
            return False
        return any(f.get('severity') == 'error' for f in obj.flags)


class EmissionRecordDetailSerializer(serializers.ModelSerializer):
    """Full serializer with raw data and audit trail."""
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    review_status_display = serializers.CharField(source='get_review_status_display', read_only=True)
    source_type = serializers.CharField(source='ingestion.source_type', read_only=True)
    source_file = serializers.CharField(source='ingestion.file_name', read_only=True)
    raw_data = serializers.SerializerMethodField()
    emission_factor_detail = EmissionFactorSerializer(source='emission_factor', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True, default='')
    locked_by_name = serializers.CharField(source='locked_by.username', read_only=True, default='')
    audit_trail = serializers.SerializerMethodField()

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'scope', 'scope_display', 'scope_category', 'activity_type',
            'quantity', 'unit', 'original_quantity', 'original_unit',
            'period_start', 'period_end', 'facility_code', 'facility_name',
            'co2e_kg', 'emission_factor', 'emission_factor_detail',
            'review_status', 'review_status_display', 'flags',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_notes',
            'is_locked', 'locked_at', 'locked_by', 'locked_by_name',
            'created_at', 'updated_at', 'version',
            'source_type', 'source_file', 'raw_data', 'audit_trail',
        ]

    def get_raw_data(self, obj):
        if obj.raw_record:
            return obj.raw_record.raw_data
        return None

    def get_audit_trail(self, obj):
        from review.serializers import AuditLogSerializer
        logs = obj.audit_logs.all().order_by('-performed_at')[:20]
        return AuditLogSerializer(logs, many=True).data
