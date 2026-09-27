from django.db import IntegrityError
from django.db.models import (
    DecimalField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
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
    PaymentSerializer,
    SalesInvoiceSerializer,
    SalesInvoicePostSerializer,
    SalesSettingsSerializer,
)
from apps.sales.services import (
    CustomerService,
    PaymentService,
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
        code = data.get("code")
        try:
            customer, created = CustomerService(request.tenant_id).create_with_flag(
                name=data["name"],
                email=data.get("email"),
                phone=data.get("phone"),
                address=data.get("address"),
                tax_id=data.get("tax_id"),
                code=code,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
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
        qs = qs.annotate(
            paid_amount=Coalesce(
                Sum(
                    "payments__amount",
                    filter=Q(payments__status=models.Payment.Status.POSTED),
                ),
                Value(0, output_field=DecimalField(max_digits=19, decimal_places=4)),
            )
        ).order_by("-created_at", "-id")
        return qs.prefetch_related("lines").select_related("customer")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = SalesInvoiceService(request.tenant_id)
        try:
            invoice = service.create_draft(
                number=data.get("number"),
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


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewSales()]
        if self.action == "post_payment":
            return [CanPostSalesInvoice()]
        return [CanManageSales()]

    def get_queryset(self):
        qs = models.Payment.objects.for_tenant(self.request.tenant_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        invoice_param = self.request.query_params.get("invoice")
        if invoice_param:
            qs = qs.filter(invoice_id=invoice_param)
        invoice_paid = (
            models.Payment.objects.filter(
                invoice_id=OuterRef("invoice_id"),
                status=models.Payment.Status.POSTED,
            )
            .values("invoice_id")
            .annotate(total=Sum("amount"))
            .values("total")
        )
        qs = qs.annotate(
            _invoice_paid=Coalesce(
                Subquery(invoice_paid),
                Value(0, output_field=DecimalField(max_digits=19, decimal_places=4)),
            )
        ).order_by("-created_at", "-id")
        return qs.select_related("invoice__customer", "cash_account")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = PaymentService(request.tenant_id)
        try:
            payment = service.create_draft(
                number=data["number"],
                invoice_id=data["invoice_id"].pk,
                payment_date=data["payment_date"],
                amount=data["amount"],
                method=data["method"],
                cash_account=data["cash_account"].pk,
                reference=data.get("reference"),
                notes=data.get("notes"),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            PaymentSerializer(payment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = PaymentService(request.tenant_id)
        try:
            payment = service.update_draft(
                kwargs["pk"],
                number=data["number"] if "number" in data else None,
                invoice_id=data["invoice_id"].pk if "invoice_id" in data else None,
                payment_date=(
                    data["payment_date"] if "payment_date" in data else None
                ),
                amount=data["amount"] if "amount" in data else None,
                method=data["method"] if "method" in data else None,
                cash_account=(
                    data["cash_account"].pk if "cash_account" in data else None
                ),
                reference=data["reference"] if "reference" in data else _UNSET,
                notes=data["notes"] if "notes" in data else _UNSET,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            PaymentSerializer(payment, context={"request": request}).data
        )

    def destroy(self, request, *args, **kwargs):
        service = PaymentService(request.tenant_id)
        try:
            service.delete_draft(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[CanPostSalesInvoice])
    def post_payment(self, request, pk=None):
        service = PaymentService(request.tenant_id)
        try:
            payment = service.post_payment(pk)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            PaymentSerializer(payment, context={"request": request}).data
        )


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