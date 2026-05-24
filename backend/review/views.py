"""Review views for approve/reject/lock workflow."""
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from emissions.models import EmissionRecord
from review.models import AuditLog
from review.serializers import BulkActionSerializer, AuditLogSerializer


def _get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_records(request):
    """Approve one or more emission records."""
    serializer = BulkActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    record_ids = serializer.validated_data['record_ids']
    notes = serializer.validated_data['notes']
    ip = _get_client_ip(request)

    records = EmissionRecord.objects.filter(
        id__in=record_ids,
        tenant=request.user.tenant,
        is_locked=False,
    )

    updated = 0
    for record in records:
        old_status = record.review_status
        record.review_status = 'approved'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.review_notes = notes
        record.version += 1
        record.save()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            emission_record=record,
            action='approved',
            field_changed='review_status',
            old_value=old_status,
            new_value='approved',
            performed_by=request.user,
            ip_address=ip,
            metadata={'notes': notes},
        )
        updated += 1

    return Response({'updated': updated, 'message': f'{updated} records approved'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_records(request):
    """Reject one or more emission records."""
    serializer = BulkActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    record_ids = serializer.validated_data['record_ids']
    notes = serializer.validated_data['notes']
    ip = _get_client_ip(request)

    records = EmissionRecord.objects.filter(
        id__in=record_ids,
        tenant=request.user.tenant,
        is_locked=False,
    )

    updated = 0
    for record in records:
        old_status = record.review_status
        record.review_status = 'rejected'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.review_notes = notes
        record.version += 1
        record.save()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            emission_record=record,
            action='rejected',
            field_changed='review_status',
            old_value=old_status,
            new_value='rejected',
            performed_by=request.user,
            ip_address=ip,
            metadata={'notes': notes},
        )
        updated += 1

    return Response({'updated': updated, 'message': f'{updated} records rejected'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lock_records(request):
    """Lock approved records for audit (makes them immutable)."""
    serializer = BulkActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    record_ids = serializer.validated_data['record_ids']
    ip = _get_client_ip(request)

    # Only approved records can be locked
    records = EmissionRecord.objects.filter(
        id__in=record_ids,
        tenant=request.user.tenant,
        review_status='approved',
        is_locked=False,
    )

    locked = 0
    for record in records:
        record.is_locked = True
        record.locked_at = timezone.now()
        record.locked_by = request.user
        record.save()

        AuditLog.objects.create(
            tenant=request.user.tenant,
            emission_record=record,
            action='locked',
            field_changed='is_locked',
            old_value='False',
            new_value='True',
            performed_by=request.user,
            ip_address=ip,
        )
        locked += 1

    return Response({'locked': locked, 'message': f'{locked} records locked for audit'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_trail(request):
    """Get audit trail for the tenant, optionally filtered by record."""
    record_id = request.query_params.get('record_id')

    qs = AuditLog.objects.filter(tenant=request.user.tenant)
    if record_id:
        qs = qs.filter(emission_record_id=record_id)

    qs = qs.order_by('-performed_at')[:100]

    return Response(AuditLogSerializer(qs, many=True).data)
