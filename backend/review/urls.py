"""Review URL configuration."""
from django.urls import path
from review.views import approve_records, reject_records, lock_records, audit_trail

urlpatterns = [
    path('approve/', approve_records, name='approve_records'),
    path('reject/', reject_records, name='reject_records'),
    path('lock/', lock_records, name='lock_records'),
    path('audit-trail/', audit_trail, name='audit_trail'),
]
