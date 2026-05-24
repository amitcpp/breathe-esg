"""Admin registration for all models."""
from django.contrib import admin
from core.models import Tenant, User

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'tenant', 'is_active']
    list_filter = ['role', 'tenant']
    search_fields = ['username', 'email']
