from django.db import IntegrityError

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import Http404

from apps.accounting import models
from apps.accounting.serializers import (
    AccountSerializer,
    JournalEntrySerializer,
    JournalEntryPostSerializer,
    LedgerSerializer,
    TrialBalanceSerializer,
    IncomeStatementSerializer,
    BalanceSheetSerializer,
)
from apps.accounting.services import (
    AccountingService,
    JournalEntryService,
    LedgerService,
    ReportService,
)
from apps.accounting.permissions import HasAccountingAccess, CanViewReports


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [HasAccountingAccess]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        svc = AccountingService(self.request.tenant_id)
        type_filter = self.request.query_params.get("type")
        tree_mode = self.request.query_params.get("tree", "").lower() == "true"
        if tree_mode:
            return svc.list_accounts_tree(type=type_filter)
        return svc.list_accounts(type=type_filter)

    def get_object(self):
        svc = AccountingService(self.request.tenant_id)
        lookup = self.kwargs.get(self.lookup_field)
        try:
            return svc.get_account(lookup)
        except models.Account.DoesNotExist:
            raise Http404

    def create(self, request, *args, **kwargs):
        svc = AccountingService(request.tenant_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = svc.create_account(
            name=serializer.validated_data["name"],
            account_type=serializer.validated_data["type"],
            parent_id=serializer.validated_data.get("parent_id"),
            description=serializer.validated_data.get("description"),
        )
        output = self.get_serializer(account).data
        return Response(output, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        svc = AccountingService(request.tenant_id)
        account = self.get_object()
        serializer = self.get_serializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_kwargs = dict(serializer.validated_data)
        if update_kwargs.get("is_active") is False:
            try:
                svc.deactivate_account(account.pk)
            except ValueError:
                pass
            update_kwargs.pop("is_active", None)
        if update_kwargs:
            try:
                svc.update_account(account.pk, **update_kwargs)
            except ValueError:
                pass
        output = self.get_serializer(svc.get_account(account.pk)).data
        return Response(output)


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
        try:
            entry = svc.create_entry(
                date=serializer.validated_data["date"],
                description=serializer.validated_data["description"],
                reference=serializer.validated_data["reference"],
                lines_data=serializer.validated_data["lines"],
            )
        except IntegrityError:
            return Response(
                {"detail": "A journal entry with this reference already exists for this tenant."},
                status=status.HTTP_400_BAD_REQUEST,
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

    @action(detail=True, methods=["post"], url_path="post")
    def post(self, request, pk=None):
        svc = JournalEntryService(request.tenant_id)
        try:
            entry = svc.post_entry(pk)
        except models.JournalEntry.DoesNotExist:
            return Response(
                {"detail": "Journal entry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        output = JournalEntryPostSerializer(entry).data
        return Response(output)


class LedgerViewSet(viewsets.GenericViewSet):
    serializer_class = LedgerSerializer
    permission_classes = [HasAccountingAccess]

    def list(self, request, *args, **kwargs):
        account_id = request.query_params.get("account_id")
        if not account_id:
            return Response(
                {"detail": "account_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        svc = LedgerService(request.tenant_id)
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        try:
            data = svc.get_ledger(account_id, date_from=date_from, date_to=date_to)
        except models.Account.DoesNotExist:
            return Response(
                {"detail": "Account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(data)
        return Response(serializer.data)


class ReportViewSet(viewsets.GenericViewSet):
    permission_classes = [CanViewReports]

    def get_serializer_class(self):
        action = self.request.query_params.get("type") or "trial-balance"
        return TrialBalanceSerializer

    @action(detail=False, methods=["get"], url_path="trial-balance")
    def trial_balance(self, request):
        svc = ReportService(request.tenant_id)
        data = svc.trial_balance(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return Response(TrialBalanceSerializer(data).data)

    @action(detail=False, methods=["get"], url_path="income-statement")
    def income_statement(self, request):
        svc = ReportService(request.tenant_id)
        data = svc.income_statement(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return Response(IncomeStatementSerializer(data).data)

    @action(detail=False, methods=["get"], url_path="balance-sheet")
    def balance_sheet(self, request):
        svc = ReportService(request.tenant_id)
        data = svc.balance_sheet(
            as_of=request.query_params.get("as_of"),
        )
        return Response(BalanceSheetSerializer(data).data)
