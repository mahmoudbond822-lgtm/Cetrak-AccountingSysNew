from django.db import IntegrityError, transaction

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.inventory import models
from apps.inventory.permissions import (
    CanConfigureInventory,
    CanManageInventory,
    CanViewInventory,
)
from apps.inventory.serializers import (
    InventorySettingsSerializer,
    ProductSerializer,
    StockAdjustmentPostSerializer,
    StockAdjustmentSerializer,
    StockBalanceSerializer,
    StockMovementSerializer,
    WarehouseSerializer,
)
from apps.inventory.services import (
    InventorySettingsService,
    StockAdjustmentService,
    _UNSET,
)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewInventory()]
        return [CanManageInventory()]

    def get_queryset(self):
        qs = models.Product.objects.for_tenant(self.request.tenant_id)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs.order_by("sku")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            with transaction.atomic():
                product = models.Product.objects.create(
                    tenant_id=request.tenant_id,
                    sku=data["sku"],
                    name=data["name"],
                    unit=data["unit"],
                    is_active=data.get("is_active", True),
                )
        except IntegrityError:
            return Response(
                {"detail": "Product SKU already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            ProductSerializer(product).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                product = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "Product SKU already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(product).data)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if (
            models.StockMovement.objects.for_tenant(request.tenant_id)
            .filter(product_id=product.pk)
            .exists()
            or models.StockBalance.objects.for_tenant(request.tenant_id)
            .filter(product_id=product.pk)
            .exists()
        ):
            return Response(
                {
                    "detail": (
                        "Product has stock movements and cannot be deleted. "
                        "Deactivate instead."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class WarehouseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [CanViewInventory]

    def get_queryset(self):
        qs = models.Warehouse.objects.for_tenant(self.request.tenant_id)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs.order_by("name")


class StockBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockBalanceSerializer
    permission_classes = [CanViewInventory]

    def get_queryset(self):
        qs = models.StockBalance.objects.for_tenant(
            self.request.tenant_id
        ).select_related("product", "warehouse")
        product_id = self.request.query_params.get("product_id")
        if product_id:
            qs = qs.filter(product_id=product_id)
        warehouse_id = self.request.query_params.get("warehouse_id")
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        return qs.order_by("product__sku")


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [CanViewInventory]

    def get_queryset(self):
        qs = models.StockMovement.objects.for_tenant(
            self.request.tenant_id
        ).select_related(
            "product",
            "warehouse",
            "purchase_invoice",
            "sales_invoice",
            "adjustment",
        )
        product_id = self.request.query_params.get("product_id")
        if product_id:
            qs = qs.filter(product_id=product_id)
        warehouse_id = self.request.query_params.get("warehouse_id")
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        movement_type = self.request.query_params.get("movement_type")
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        return qs.order_by("-created_at")


class StockAdjustmentViewSet(viewsets.ModelViewSet):
    serializer_class = StockAdjustmentSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewInventory()]
        return [CanManageInventory()]

    def get_queryset(self):
        qs = models.StockAdjustment.objects.for_tenant(
            self.request.tenant_id
        ).prefetch_related("lines__product")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = StockAdjustmentService(request.tenant_id)
        lines_data = [
            {"product_id": line["product_id"].pk, "quantity": line["quantity"]}
            for line in data.get("lines", [])
        ]
        try:
            adjustment = service.create_draft(
                number=data["number"],
                adjustment_date=data["adjustment_date"],
                reason=data["reason"],
                notes=data.get("notes"),
                lines_data=lines_data,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            StockAdjustmentSerializer(
                adjustment, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = StockAdjustmentService(request.tenant_id)
        if "lines" in data:
            lines_data = [
                {
                    "product_id": line["product_id"].pk,
                    "quantity": line["quantity"],
                }
                for line in data["lines"]
            ]
        else:
            lines_data = None
        try:
            adjustment = service.update_draft(
                kwargs["pk"],
                number=data["number"] if "number" in data else None,
                adjustment_date=(
                    data["adjustment_date"]
                    if "adjustment_date" in data
                    else None
                ),
                reason=data["reason"] if "reason" in data else None,
                notes=data["notes"] if "notes" in data else _UNSET,
                lines_data=lines_data,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            StockAdjustmentSerializer(
                adjustment, context={"request": request}
            ).data
        )

    def destroy(self, request, *args, **kwargs):
        service = StockAdjustmentService(request.tenant_id)
        try:
            service.delete_draft(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[CanManageInventory])
    def post_adjustment(self, request, pk=None):
        service = StockAdjustmentService(request.tenant_id)
        try:
            adjustment = service.post_adjustment(pk)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(StockAdjustmentPostSerializer(adjustment).data)


class InventorySettingsViewSet(viewsets.GenericViewSet):
    serializer_class = InventorySettingsSerializer
    http_method_names = ["get", "put"]
    permission_classes = [CanConfigureInventory]

    def get_queryset(self):
        return models.InventorySettings.objects.for_tenant(
            self.request.tenant_id
        )

    def get_object(self):
        return InventorySettingsService(self.request.tenant_id).get()

    def retrieve(self, request, *args, **kwargs):
        settings = self.get_object()
        return Response(InventorySettingsSerializer(settings).data)

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = InventorySettingsService(request.tenant_id)
        try:
            settings = service.update(**data)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(InventorySettingsSerializer(settings).data)