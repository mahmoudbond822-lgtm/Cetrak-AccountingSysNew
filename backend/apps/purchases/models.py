from django.db import models

from apps.core.models import TenantOwnedLineModel, TenantScopedModel


class Vendor(TenantScopedModel):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "purchase_vendor"
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                name="unique_vendor_code_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class PurchaseInvoice(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        POSTED = "Posted", "Posted"

    number = models.CharField(max_length=50)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(null=True, blank=True)
    discount = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    subtotal = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    tax = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_journal = models.OneToOneField(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_invoice",
    )

    class Meta:
        db_table = "purchase_invoice"
        verbose_name = "Purchase Invoice"
        verbose_name_plural = "Purchase Invoices"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                name="unique_purchase_invoice_number_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["vendor"]),
            models.Index(fields=["tenant", "vendor", "invoice_date"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} ({self.status})"


class PurchaseInvoiceLine(TenantOwnedLineModel):
    parent_field = "invoice"

    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=19, decimal_places=4)
    unit_price = models.DecimalField(max_digits=19, decimal_places=4)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    tax = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    total = models.DecimalField(max_digits=19, decimal_places=4, default=0)

    class Meta:
        db_table = "purchase_invoiceline"
        verbose_name = "Purchase Invoice Line"
        verbose_name_plural = "Purchase Invoice Lines"
        indexes = [
            models.Index(
                fields=["tenant", "invoice"],
                name="purch_line_tenant_invoice_idx",
            ),
        ]

    def __str__(self):
        return f"{self.description} x {self.quantity}"


class PurchaseSettings(TenantScopedModel):
    accounts_payable = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    expense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    input_vat = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "purchase_settings"
        verbose_name = "Purchase Settings"
        verbose_name_plural = "Purchase Settings"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="unique_purchase_settings_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Purchase settings (tenant {self.tenant_id})"