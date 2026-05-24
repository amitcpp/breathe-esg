"""
URL configuration for Breathe ESG project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('core.urls')),
    path('api/ingestion/', include('ingestion.urls')),
    path('api/emissions/', include('emissions.urls')),
    path('api/review/', include('review.urls')),
    path('api/dashboard/', include('emissions.dashboard_urls')),
]
