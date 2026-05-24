"""Ingestion URL configuration."""
from django.urls import path
from ingestion.views import upload_file, IngestionHistoryView, IngestionDetailView

urlpatterns = [
    path('upload/', upload_file, name='upload_file'),
    path('history/', IngestionHistoryView.as_view(), name='ingestion_history'),
    path('history/<uuid:id>/', IngestionDetailView.as_view(), name='ingestion_detail'),
]
