from rest_framework import viewsets, status
from rest_framework.response import Response

from apps.accounting import models
from apps.accounting.serializers import AccountSerializer, JournalEntrySerializer
from apps.accounting.services import AccountingService, JournalEntryService
from apps.accounting.permissions import HasAccountingAccess


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [HasAccountingAccess]

    def get_queryset(self):
        svc = AccountingService(self.request.tenant_id)
        type_filter = self.request.query_params.get("type")
        tree_mode = self.request.query_params.get("tree", "").lower() == "true"
        if tree_mode:
            return svc.list_accounts_tree(type=type_filter)
        return svc.list_accounts(type=type_filter)

    def create(self, request, *args, **kwargs):
        svc = AccountingService(request.tenant_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = svc.create_account(
            name=serializer.validated_data["name"],
            type=serializer.validated_data["type"],
            parent_id=serializer.validated_data.get("parent_id"),
            description=serializer.validated_data.get("description"),
        )
        output = self.get_serializer(account).data
        return Response(output, status=status.HTTP_201_CREATED)


class JournalEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [HasAccountingAccess]

    def get_queryset(self):
        svc = JournalEntryService(self.request.tenant_id)
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        return svc.list_entries(date_from=date_from, date_to=date_to)

    def create(self, request, *args, **kwargs):
        svc = JournalEntryService(request.tenant_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = svc.create_entry(
            date=serializer.validated_data["date"],
            description=serializer.validated_data["description"],
            reference=serializer.validated_data["reference"],
            lines_data=serializer.validated_data["lines"],
        )
        output = self.get_serializer(entry).data
        return Response(output, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Journal entries are immutable and cannot be modified."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Journal entries are immutable and cannot be modified."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Journal entries are immutable and cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
