from django.db import models

from apps.core.models import TenantOwnedLineModel, TenantScopedModel


class Product(TenantScopedModel):
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "inventory_product"
        verbose_name = "Product"
        verbose_name_plural = "Products"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                name="unique_product_sku_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Warehouse(TenantScopedModel):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "inventory_warehouse"
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"],
                name="unique_warehouse_name_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant"]),
        ]

    def __str__(self):
        return self.name


class InventorySettings(TenantScopedModel):
    inventory_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    cogs_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    adjustments_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    default_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "inventory_settings"
        verbose_name = "Inventory Settings"
        verbose_name_plural = "Inventory Settings"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="unique_inventory_settings_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Inventory settings (tenant {self.tenant_id})"


class StockBalance(TenantScopedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="balances",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="balances",
    )
    quantity = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    value = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    moving_avg_cost = models.DecimalField(max_digits=19, decimal_places=4, default=0)

    class Meta:
        db_table = "inventory_stockbalance"
        verbose_name = "Stock Balance"
        verbose_name_plural = "Stock Balances"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "product", "warehouse"],
                name="unique_stockbalance_per_product_warehouse",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "product", "warehouse"]),
        ]

    def __str__(self):
        return f"{self.product_id} @ {self.warehouse_id}: {self.quantity}"


class StockMovement(TenantScopedModel):
    class MovementType(models.TextChoices):
        RECEIPT = "Receipt", "Receipt"
        ISSUE = "Issue", "Issue"
        ADJUSTMENT = "Adjustment", "Adjustment"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=19, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=19, decimal_places=4)
    value = models.DecimalField(max_digits=19, decimal_places=4)
    purchase_invoice = models.ForeignKey(
        "purchases.PurchaseInvoice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    sales_invoice = models.ForeignKey(
        "sales.SalesInvoice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    adjustment = models.ForeignKey(
        "inventory.StockAdjustment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
    )

    class Meta:
        db_table = "inventory_stockmovement"
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        indexes = [
            models.Index(fields=["tenant", "product", "warehouse"]),
            models.Index(fields=["tenant", "movement_type"]),
            models.Index(fields=["tenant", "purchase_invoice"]),
            models.Index(fields=["tenant", "sales_invoice"]),
            models.Index(fields=["tenant", "adjustment"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} x {self.product_id}"


class StockAdjustment(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        POSTED = "Posted", "Posted"

    number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    adjustment_date = models.DateField()
    reason = models.CharField(max_length=255)
    notes = models.TextField(null=True, blank=True)
    posted_journal = models.OneToOneField(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_adjustment",
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inventory_stockadjustment"
        verbose_name = "Stock Adjustment"
        verbose_name_plural = "Stock Adjustments"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                name="unique_adjustment_number_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "adjustment_date"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} ({self.status})"


class StockAdjustmentLine(TenantOwnedLineModel):
    parent_field = "adjustment"

    adjustment = models.ForeignKey(
        StockAdjustment,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="adjustment_lines",
    )
    quantity = models.DecimalField(max_digits=19, decimal_places=4)

    class Meta:
        db_table = "inventory_stockadjustmentline"
        verbose_name = "Stock Adjustment Line"
        verbose_name_plural = "Stock Adjustment Lines"
        indexes = [
            models.Index(
                fields=["tenant", "adjustment"],
                name="inv_line_tenant_adj_idx",
            ),
        ]

    def __str__(self):
        return f"{self.product_id}: {self.quantity}"