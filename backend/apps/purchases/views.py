from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.purchases import models
from apps.purchases.permissions import (
    CanConfigurePurchases,
    CanManagePurchases,
    CanPostPurchaseInvoice,
    CanViewPurchases,
)
from apps.purchases.serializers import (
    PurchaseInvoicePostSerializer,
    PurchaseInvoiceSerializer,
    PurchasePaymentSerializer,
    PurchaseSettingsSerializer,
    VendorSerializer,
)
from apps.purchases.services import (
    PurchaseInvoiceService,
    PurchaseSettingsService,
    VendorService,
    _UNSET,
)
from apps.sales.models import Payment
from apps.sales.services import PaymentService


class VendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewPurchases()]
        return [CanManagePurchases()]

    def get_queryset(self):
        qs = models.Vendor.objects.for_tenant(self.request.tenant_id)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs.order_by("code")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        code = data.get("code")
        try:
            vendor, created = VendorService(request.tenant_id).create_with_flag(
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
        except IntegrityError:
            return Response(
                {"detail": "Vendor code already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.get_serializer(vendor).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        vendor = self.get_object()
        serializer = self.get_serializer(vendor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            vendor = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "Vendor code already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(vendor).data)

    def destroy(self, request, *args, **kwargs):
        vendor = self.get_object()
        if vendor.invoices.exists():
            return Response(
                {
                    "detail": (
                        "Vendor has purchase invoices and cannot be deleted. "
                        "Deactivate instead."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        vendor.is_active = False
        vendor.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseInvoiceSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewPurchases()]
        return [CanManagePurchases()]

    def get_queryset(self):
        qs = models.PurchaseInvoice.objects.for_tenant(self.request.tenant_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.prefetch_related("lines").select_related("vendor")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = PurchaseInvoiceService(request.tenant_id)
        try:
            invoice = service.create_draft(
                number=data.get("number"),
                vendor_id=data["vendor_id"].pk,
                invoice_date=data["invoice_date"],
                due_date=data.get("due_date"),
                discount=data.get("discount"),
                notes=data.get("notes"),
                lines_data=data.get("lines", []),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            PurchaseInvoiceSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = PurchaseInvoiceService(request.tenant_id)
        try:
            invoice = service.update_draft(
                kwargs["pk"],
                vendor_id=(
                    data["vendor_id"].pk if "vendor_id" in data else None
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
        return Response(PurchaseInvoiceSerializer(invoice).data)

    def destroy(self, request, *args, **kwargs):
        service = PurchaseInvoiceService(request.tenant_id)
        try:
            service.delete_invoice(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[CanPostPurchaseInvoice])
    def post_invoice(self, request, pk=None):
        service = PurchaseInvoiceService(request.tenant_id)
        try:
            invoice = service.post_invoice(pk)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(PurchaseInvoicePostSerializer(invoice).data)


class PurchasePaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PurchasePaymentSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewPurchases()]
        if self.action == "post_payment":
            return [CanPostPurchaseInvoice()]
        return [CanManagePurchases()]

    def get_queryset(self):
        qs = Payment.objects.for_tenant(self.request.tenant_id).filter(
            direction=Payment.Direction.PAYABLE
        )
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        invoice_param = self.request.query_params.get("purchase_invoice")
        if invoice_param:
            qs = qs.filter(purchase_invoice_id=invoice_param)
        return qs.select_related("purchase_invoice__vendor", "cash_account")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = PaymentService(request.tenant_id)
        try:
            payment = service.create_draft(
                number=data["number"],
                direction=Payment.Direction.PAYABLE,
                purchase_invoice_id=data["purchase_invoice_id"].pk,
                payment_date=data["payment_date"],
                amount=data.get("amount"),
                method=data["method"],
                cash_account=data["cash_account"].pk,
                reference=data.get("reference"),
                notes=data.get("notes"),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            PurchasePaymentSerializer(payment, context={"request": request}).data,
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
                purchase_invoice_id=(
                    data["purchase_invoice_id"].pk
                    if "purchase_invoice_id" in data
                    else None
                ),
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
            PurchasePaymentSerializer(payment, context={"request": request}).data
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

    @action(detail=True, methods=["post"], permission_classes=[CanPostPurchaseInvoice])
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
            PurchasePaymentSerializer(payment, context={"request": request}).data
        )


class PurchaseSettingsViewSet(viewsets.GenericViewSet):
    serializer_class = PurchaseSettingsSerializer
    http_method_names = ["get", "put"]
    permission_classes = [CanConfigurePurchases]

    def get_queryset(self):
        return models.PurchaseSettings.objects.for_tenant(self.request.tenant_id)

    def get_object(self):
        return PurchaseSettingsService(self.request.tenant_id).get()

    def retrieve(self, request, *args, **kwargs):
        settings = self.get_object()
        return Response(PurchaseSettingsSerializer(settings).data)

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = PurchaseSettingsService(request.tenant_id)
        try:
            settings = service.update(**data)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(PurchaseSettingsSerializer(settings).data)