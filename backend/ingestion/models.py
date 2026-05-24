"""
Ingestion models: DataIngestion and RawRecord.

DataIngestion tracks each file upload event. RawRecord stores every row
from the source file as raw JSON, preserving the original data for
audit purposes regardless of whether parsing succeeds.
"""
import uuid
from django.db import models
from core.models import Tenant, User


class DataIngestion(models.Model):
    """
    Represents a single file upload / ingestion event.
    
    Tracks the lifecycle from upload through parsing and normalization.
    The processing_log field captures detailed parse/validation messages
    so analysts can diagnose import failures.
    """
    SOURCE_TYPE_CHOICES = [
        ('sap_fuel', 'SAP Fuel & Procurement'),
        ('utility_electricity', 'Utility Electricity'),
        ('travel', 'Corporate Travel'),
    ]

    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('completed_with_errors', 'Completed with Errors'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ingestions')
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES)
    file_name = models.CharField(max_length=500, help_text="Original uploaded filename")
    file_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash for duplicate detection"
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='processing')
    row_count = models.IntegerField(default=0, help_text="Total rows parsed from file")
    success_count = models.IntegerField(default=0, help_text="Rows successfully normalized")
    error_count = models.IntegerField(default=0, help_text="Rows that failed parsing/validation")
    processing_log = models.JSONField(
        default=list,
        blank=True,
        help_text="Detailed log of parsing and validation messages"
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = 'Data ingestions'

    def __str__(self):
        return f"{self.get_source_type_display()} - {self.file_name} ({self.status})"


class RawRecord(models.Model):
    """
    Stores each row from a source file as raw JSON.
    
    This is the source-of-truth: the original data exactly as it appeared
    in the uploaded file, before any normalization. Every EmissionRecord
    links back to its RawRecord so analysts can always see what came in.
    
    The parse_status tracks whether this row was successfully converted
    to a normalized EmissionRecord.
    """
    PARSE_STATUS_CHOICES = [
        ('parsed', 'Successfully Parsed'),
        ('failed', 'Parse Failed'),
        ('skipped', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingestion = models.ForeignKey(
        DataIngestion,
        on_delete=models.CASCADE,
        related_name='raw_records'
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='raw_records',
        help_text="Denormalized from ingestion for query performance"
    )
    row_number = models.IntegerField(help_text="Line number in the source file (1-indexed)")
    raw_data = models.JSONField(help_text="Complete original row as key-value pairs")
    parse_status = models.CharField(max_length=20, choices=PARSE_STATUS_CHOICES, default='parsed')
    parse_errors = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of error messages from parsing"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ingestion', 'row_number']
        indexes = [
            models.Index(fields=['tenant', 'ingestion']),
            models.Index(fields=['parse_status']),
        ]

    def __str__(self):
        return f"Row {self.row_number} of {self.ingestion.file_name}"
