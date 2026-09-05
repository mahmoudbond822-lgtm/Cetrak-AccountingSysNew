from django.contrib import admin

from apps.inventory.models import (
    InventorySettings,
    Product,
    StockAdjustment,
    StockAdjustmentLine,
    StockBalance,
    StockMovement,
    Warehouse,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "unit", "is_active", "tenant")
    list_filter = ("is_active",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "tenant")


@admin.register(InventorySettings)
class InventorySettingsAdmin(admin.ModelAdmin):
    list_display = ("tenant", "inventory_account", "cogs_account", "default_warehouse")


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "value", "moving_avg_cost")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "warehouse",
        "movement_type",
        "quantity",
        "unit_cost",
        "value",
        "created_at",
    )
    list_filter = ("movement_type",)


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("number", "status", "adjustment_date", "reason", "tenant")
    list_filter = ("status",)


@admin.register(StockAdjustmentLine)
class StockAdjustmentLineAdmin(admin.ModelAdmin):
    list_display = ("adjustment", "product", "quantity")