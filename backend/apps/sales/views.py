from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.sales import models
from apps.sales.permissions import (
    CanConfigureSales,
    CanManageSales,
    CanPostSalesInvoice,
    CanViewSales,
)
from apps.sales.serializers import (
    CustomerSerializer,
    SalesInvoiceSerializer,
    SalesInvoicePostSerializer,
    SalesSettingsSerializer,
)
from apps.sales.services import (
    SalesInvoiceService,
    SalesSettingsService,
    _UNSET,
)


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewSales()]
        return [CanManageSales()]

    def get_queryset(self):
        return models.Customer.objects.for_tenant(self.request.tenant_id).order_by("code")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            customer, created = models.Customer.objects.get_or_create(
                tenant_id=request.tenant_id,
                code=data["code"],
                defaults={k: v for k, v in data.items() if k != "code"},
            )
        except IntegrityError:
            return Response(
                {"detail": "Customer code already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.get_serializer(customer).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        customer = self.get_object()
        serializer = self.get_serializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            customer = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "Customer code already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(customer).data)

    def destroy(self, request, *args, **kwargs):
        customer = self.get_object()
        if customer.invoices.exists():
            return Response(
                {"detail": "Customer has invoices and cannot be deleted. Deactivate instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        customer.is_active = False
        customer.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SalesInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = SalesInvoiceSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewSales()]
        return [CanManageSales()]

    def get_queryset(self):
        qs = models.SalesInvoice.objects.for_tenant(self.request.tenant_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.prefetch_related("lines").select_related("customer")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = SalesInvoiceService(request.tenant_id)
        try:
            invoice = service.create_draft(
                number=data["number"],
                customer_id=data["customer_id"].pk,
                invoice_date=data["invoice_date"],
                due_date=data.get("due_date"),
                discount=data.get("discount"),
                notes=data.get("notes"),
                lines_data=data.get("lines", []),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            SalesInvoiceSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = SalesInvoiceService(request.tenant_id)
        try:
            invoice = service.update_draft(
                kwargs["pk"],
                number=data["number"] if "number" in data else None,
                customer_id=(
                    data["customer_id"].pk if "customer_id" in data else None
                ),
                invoice_date=(
                    data["invoice_date"] if "invoice_date" in data else None
                ),
                due_date=data["due_date"] if "due_date" in data else _UNSET,
                discount=data["discount"] if "discount" in data else None,
                notes=data["notes"] if "notes" in data else _UNSET,
                lines_data=data["lines"] if "lines" in data else None,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(SalesInvoiceSerializer(invoice).data)

    def destroy(self, request, *args, **kwargs):
        service = SalesInvoiceService(request.tenant_id)
        try:
            service.delete_invoice(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[CanPostSalesInvoice])
    def post_invoice(self, request, pk=None):
        service = SalesInvoiceService(request.tenant_id)
        try:
            invoice = service.post_invoice(pk)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SalesInvoicePostSerializer(invoice).data)


class SalesSettingsViewSet(viewsets.GenericViewSet):
    serializer_class = SalesSettingsSerializer
    http_method_names = ["get", "put"]
    permission_classes = [CanConfigureSales]

    def get_queryset(self):
        return models.SalesSettings.objects.for_tenant(self.request.tenant_id)

    def get_object(self):
        return SalesSettingsService(self.request.tenant_id).get()

    def retrieve(self, request, *args, **kwargs):
        settings = self.get_object()
        return Response(SalesSettingsSerializer(settings).data)

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = SalesSettingsService(request.tenant_id)
        try:
            settings = service.update(**data)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(SalesSettingsSerializer(settings).data)