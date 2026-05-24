"""
Review models: AuditLog.

Immutable audit trail that records every action taken on emission records.
This is critical for ESG compliance — auditors need to see the complete
history of how data was ingested, reviewed, modified, and approved.
"""
import uuid
from django.db import models
from core.models import Tenant, User


class AuditLog(models.Model):
    """
    Immutable audit log entry.
    
    Every significant action on an EmissionRecord creates an AuditLog entry.
    These entries cannot be modified or deleted (enforced at the application
    level — in production, you'd also use database triggers or append-only tables).
    
    The field_changed / old_value / new_value fields track field-level changes
    so auditors can see exactly what was modified and by whom.
    """
    ACTION_CHOICES = [
        ('created', 'Record Created'),
        ('updated', 'Record Updated'),
        ('approved', 'Record Approved'),
        ('rejected', 'Record Rejected'),
        ('flagged', 'Record Flagged'),
        ('locked', 'Record Locked for Audit'),
        ('unlocked', 'Record Unlocked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='audit_logs')
    emission_record = models.ForeignKey(
        'emissions.EmissionRecord',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    field_changed = models.CharField(
        max_length=100,
        blank=True,
        help_text="Which field was modified (empty for create/approve/reject)"
    )
    old_value = models.TextField(blank=True, help_text="Previous value")
    new_value = models.TextField(blank=True, help_text="New value")
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_actions'
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context, e.g. ingestion_id, batch info"
    )

    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['tenant', 'emission_record']),
            models.Index(fields=['action']),
            models.Index(fields=['performed_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.performed_by} at {self.performed_at}"
