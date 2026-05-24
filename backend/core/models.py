"""
Core models: Tenant and User.

Multi-tenancy is implemented via a shared database with tenant_id FK on all models.
This is the pragmatic choice for a prototype — schema-per-tenant adds migration
complexity without meaningful benefit at this scale.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    """
    Represents a client company. All data is scoped to a tenant.
    
    In a production system, this would also hold subscription tier,
    data residency preferences, and SSO configuration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Company name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-safe identifier")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    
    Every user belongs to exactly one tenant. The role field controls
    what actions they can perform in the review workflow.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('analyst', 'Analyst'),
        ('viewer', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,  # Null allowed for superusers created via createsuperuser
        blank=True,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='analyst')

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
