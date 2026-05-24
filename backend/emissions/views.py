"""Emissions views for querying and dashboard."""
from django.db.models import Sum, Count, Q
from rest_framework import generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from emissions.models import EmissionRecord
from emissions.serializers import EmissionRecordListSerializer, EmissionRecordDetailSerializer


class EmissionRecordListView(generics.ListAPIView):
    """List emission records with filtering."""
    serializer_class = EmissionRecordListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = {
        'scope': ['exact'],
        'review_status': ['exact'],
        'activity_type': ['exact'],
        'is_locked': ['exact'],
        'ingestion__source_type': ['exact'],
    }
    ordering_fields = ['created_at', 'co2e_kg', 'period_start', 'review_status']
    ordering = ['-created_at']
    search_fields = ['facility_name', 'facility_code', 'activity_type']

    def get_queryset(self):
        qs = EmissionRecord.objects.select_related('ingestion', 'raw_record')
        if self.request.user.tenant:
            qs = qs.filter(tenant=self.request.user.tenant)
        return qs


class EmissionRecordDetailView(generics.RetrieveAPIView):
    """Get full details of a single emission record."""
    serializer_class = EmissionRecordDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        qs = EmissionRecord.objects.select_related(
            'ingestion', 'raw_record', 'emission_factor',
            'reviewed_by', 'locked_by'
        ).prefetch_related('audit_logs')
        if self.request.user.tenant:
            qs = qs.filter(tenant=self.request.user.tenant)
        return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """Dashboard summary aggregations."""
    tenant = request.user.tenant
    if not tenant:
        return Response({'error': 'No tenant'}, status=400)

    qs = EmissionRecord.objects.filter(tenant=tenant)

    # Scope totals
    scope_totals = qs.values('scope').annotate(
        total_co2e=Sum('co2e_kg'),
        count=Count('id'),
    )

    # Review status counts
    status_counts = qs.values('review_status').annotate(count=Count('id'))

    # Source type totals
    source_totals = qs.values('ingestion__source_type').annotate(
        total_co2e=Sum('co2e_kg'),
        count=Count('id'),
    )

    # Flagged records count
    flagged_count = qs.exclude(flags=[]).count()

    # Total CO2e
    total_co2e = qs.aggregate(total=Sum('co2e_kg'))['total'] or 0

    # Recent ingestions
    from ingestion.models import DataIngestion
    from ingestion.serializers import DataIngestionSerializer
    recent = DataIngestion.objects.filter(tenant=tenant).order_by('-uploaded_at')[:5]

    return Response({
        'total_co2e_kg': float(total_co2e),
        'total_co2e_tonnes': float(total_co2e) / 1000,
        'scope_totals': {
            item['scope']: {
                'co2e_kg': float(item['total_co2e'] or 0),
                'count': item['count'],
            }
            for item in scope_totals
        },
        'review_status_counts': {
            item['review_status']: item['count']
            for item in status_counts
        },
        'source_totals': {
            (item['ingestion__source_type'] or 'unknown'): {
                'co2e_kg': float(item['total_co2e'] or 0),
                'count': item['count'],
            }
            for item in source_totals
        },
        'flagged_count': flagged_count,
        'total_records': qs.count(),
        'recent_ingestions': DataIngestionSerializer(recent, many=True).data,
    })
