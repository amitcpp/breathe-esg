"""Ingestion views for file upload and history."""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ingestion.models import DataIngestion
from ingestion.serializers import DataIngestionSerializer, FileUploadSerializer
from ingestion.parsers.sap_parser import SAPParser
from ingestion.parsers.utility_parser import UtilityParser
from ingestion.parsers.travel_parser import TravelParser


PARSER_MAP = {
    'sap_fuel': SAPParser,
    'utility_electricity': UtilityParser,
    'travel': TravelParser,
}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def upload_file(request):
    """
    Upload a data file for ingestion.
    
    Accepts multipart form data with:
    - file: The CSV file
    - source_type: One of sap_fuel, utility_electricity, travel
    """
    serializer = FileUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    uploaded_file = serializer.validated_data['file']
    source_type = serializer.validated_data['source_type']

    # Validate file size (10MB limit)
    if uploaded_file.size > 10 * 1024 * 1024:
        return Response(
            {'error': 'File size exceeds 10MB limit'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Read file content
    file_content = uploaded_file.read()

    # Get the appropriate parser
    parser_class = PARSER_MAP.get(source_type)
    if not parser_class:
        return Response(
            {'error': f'Unknown source type: {source_type}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check tenant
    if not request.user.tenant:
        return Response(
            {'error': 'User has no tenant assigned'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parse the file
    parser = parser_class(tenant=request.user.tenant, user=request.user)
    ingestion = parser.process_file(file_content, uploaded_file.name)

    return Response(
        DataIngestionSerializer(ingestion).data,
        status=status.HTTP_201_CREATED
    )


class IngestionHistoryView(generics.ListAPIView):
    """List all ingestion events for the current tenant."""
    serializer_class = DataIngestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DataIngestion.objects.all()
        if self.request.user.tenant:
            qs = qs.filter(tenant=self.request.user.tenant)
        return qs


class IngestionDetailView(generics.RetrieveDestroyAPIView):
    """Get or delete a specific ingestion (cascades to all related records)."""
    serializer_class = DataIngestionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        qs = DataIngestion.objects.all()
        if self.request.user.tenant:
            qs = qs.filter(tenant=self.request.user.tenant)
        return qs

    def destroy(self, request, *args, **kwargs):
        ingestion = self.get_object()
        # Cascade: delete emission records, audit logs, raw records, then ingestion
        from emissions.models import EmissionRecord
        from review.models import AuditLog
        records = EmissionRecord.objects.filter(ingestion=ingestion)
        AuditLog.objects.filter(emission_record__in=records).delete()
        records.delete()
        ingestion.raw_records.all().delete()
        ingestion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
