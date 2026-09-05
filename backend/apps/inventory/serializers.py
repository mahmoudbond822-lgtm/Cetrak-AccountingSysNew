from rest_framework import serializers

from apps.accounting.serializers import TenantScopedAccountField
from apps.inventory import models


class TenantScopedProductField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request")
        if request and hasattr(request, "tenant_id"):
            return models.Product.objects.for_tenant(request.tenant_id)
        return models.Product.objects.none()


class TenantScopedWarehouseField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request")
        if request and hasattr(request, "tenant_id"):
            return models.Warehouse.objects.for_tenant(request.tenant_id)
        return models.Warehouse.objects.none()


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = [
            "id",
            "sku",
            "name",
            "unit",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_sku(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("SKU is required.")
        return value

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Product name is required.")
        return value

    def validate_unit(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Unit is required.")
        return value


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Warehouse
        fields = [
            "id",
            "name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Warehouse name is required.")
        return value


class InventorySettingsSerializer(serializers.ModelSerializer):
    inventory_account = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    cogs_account = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    adjustments_account = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    default_warehouse = TenantScopedWarehouseField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    inventory_account_name = serializers.CharField(
        source="inventory_account.name", read_only=True, allow_null=True
    )
    cogs_account_name = serializers.CharField(
        source="cogs_account.name", read_only=True, allow_null=True
    )
    adjustments_account_name = serializers.CharField(
        source="adjustments_account.name", read_only=True, allow_null=True
    )
    default_warehouse_name = serializers.CharField(
        source="default_warehouse.name", read_only=True, allow_null=True
    )

    class Meta:
        model = models.InventorySettings
        fields = [
            "id",
            "inventory_account",
            "inventory_account_name",
            "cogs_account",
            "cogs_account_name",
            "adjustments_account",
            "adjustments_account_name",
            "default_warehouse",
            "default_warehouse_name",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        for field in (
            "inventory_account",
            "cogs_account",
            "adjustments_account",
        ):
            account = data.get(field)
            if account is None:
                continue
            expected_type = {
                "inventory_account": "Asset",
                "cogs_account": "Expense",
                "adjustments_account": "Expense",
            }[field]
            if account.type != expected_type:
                raise serializers.ValidationError(
                    {field: [f"Account must be of type {expected_type}."]}
                )
        return data


class StockBalanceSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True
    )
    quantity = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    moving_avg_cost = serializers.SerializerMethodField()

    class Meta:
        model = models.StockBalance
        fields = [
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "warehouse_id",
            "warehouse_name",
            "quantity",
            "value",
            "moving_avg_cost",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_quantity(self, obj):
        return "{:.4f}".format(obj.quantity)

    def get_value(self, obj):
        return "{:.4f}".format(obj.value)

    def get_moving_avg_cost(self, obj):
        return "{:.4f}".format(obj.moving_avg_cost)


class StockMovementSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True
    )
    quantity = serializers.SerializerMethodField()
    unit_cost = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    purchase_invoice_num = serializers.CharField(
        source="purchase_invoice.number", read_only=True, allow_null=True
    )
    sales_invoice_num = serializers.CharField(
        source="sales_invoice.number", read_only=True, allow_null=True
    )
    adjustment_num = serializers.CharField(
        source="adjustment.number", read_only=True, allow_null=True
    )

    class Meta:
        model = models.StockMovement
        fields = [
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "warehouse_id",
            "warehouse_name",
            "movement_type",
            "quantity",
            "unit_cost",
            "value",
            "purchase_invoice_num",
            "sales_invoice_num",
            "adjustment_num",
            "created_at",
        ]
        read_only_fields = fields

    def get_quantity(self, obj):
        return "{:.4f}".format(obj.quantity)

    def get_unit_cost(self, obj):
        return "{:.4f}".format(obj.unit_cost)

    def get_value(self, obj):
        return "{:.4f}".format(obj.value)


class StockAdjustmentLineSerializer(serializers.ModelSerializer):
    product_id = TenantScopedProductField(queryset=None)
    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )
    product_name = serializers.CharField(
        source="product.name", read_only=True, allow_null=True
    )
    quantity = serializers.DecimalField(max_digits=19, decimal_places=4)

    class Meta:
        model = models.StockAdjustmentLine
        fields = [
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "quantity",
        ]
        read_only_fields = ["id"]

    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError(
                "Adjustment quantity must not be zero."
            )
        return value


class StockAdjustmentSerializer(serializers.ModelSerializer):
    lines = StockAdjustmentLineSerializer(many=True)
    journal_entry_id = serializers.UUIDField(
        source="posted_journal.id", read_only=True, allow_null=True
    )

    class Meta:
        model = models.StockAdjustment
        fields = [
            "id",
            "number",
            "status",
            "adjustment_date",
            "reason",
            "notes",
            "lines",
            "journal_entry_id",
            "posted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "journal_entry_id",
            "posted_at",
            "created_at",
            "updated_at",
        ]

    def validate_number(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError(
                "Adjustment number is required."
            )
        return value

    def validate_reason(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Reason is required.")
        return value


class StockAdjustmentPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StockAdjustment
        fields = ["id", "number", "status", "posted_at", "reason"]