"""Review serializers."""
from rest_framework import serializers
from review.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.username', read_only=True, default='System')

    class Meta:
        model = AuditLog
        fields = [
            'id', 'action', 'action_display', 'field_changed',
            'old_value', 'new_value', 'performed_by', 'performed_by_name',
            'performed_at', 'metadata',
        ]


class BulkActionSerializer(serializers.Serializer):
    record_ids = serializers.ListField(child=serializers.UUIDField())
    notes = serializers.CharField(required=False, default='', allow_blank=True)
