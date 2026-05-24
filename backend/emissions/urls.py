"""Emissions URL configuration."""
from django.urls import path
from emissions.views import EmissionRecordListView, EmissionRecordDetailView

urlpatterns = [
    path('records/', EmissionRecordListView.as_view(), name='emission_records'),
    path('records/<uuid:id>/', EmissionRecordDetailView.as_view(), name='emission_record_detail'),
]
