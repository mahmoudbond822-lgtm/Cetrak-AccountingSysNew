from django.db import models

from apps.core.models import TenantScopedModel, BaseModel


class Customer(TenantScopedModel):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sales_customer"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                name="unique_customer_code_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class SalesInvoice(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        POSTED = "Posted", "Posted"

    number = models.CharField(max_length=50)
    customer = models.ForeignKey(
        Customer,
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
        related_name="sales_invoice",
    )

    class Meta:
        db_table = "sales_invoice"
        verbose_name = "Sales Invoice"
        verbose_name_plural = "Sales Invoices"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                name="unique_invoice_number_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["customer"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} ({self.status})"


class SalesInvoiceLine(BaseModel):
    invoice = models.ForeignKey(
        SalesInvoice,
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
        db_table = "sales_invoiceline"
        verbose_name = "Sales Invoice Line"
        verbose_name_plural = "Sales Invoice Lines"

    def __str__(self):
        return f"{self.description} x {self.quantity}"


class Payment(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        POSTED = "Posted", "Posted"

    class Method(models.TextChoices):
        CASH = "Cash", "Cash"
        BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
        CARD = "Card", "Card"
        CHECK = "Check", "Check"

    class Direction(models.TextChoices):
        RECEIVABLE = "Receivable", "Receivable"
        PAYABLE = "Payable", "Payable"

    number = models.CharField(max_length=50)
    direction = models.CharField(
        max_length=20,
        choices=Direction.choices,
        default=Direction.RECEIVABLE,
    )
    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )
    purchase_invoice = models.ForeignKey(
        "purchases.PurchaseInvoice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    method = models.CharField(max_length=20, choices=Method.choices)
    cash_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        related_name="+",
    )
    reference = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    journal_entry = models.OneToOneField(
        "accounting.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payment",
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sales_payment"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                name="unique_payment_number_per_tenant",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(invoice__isnull=False)
                     & models.Q(purchase_invoice__isnull=True))
                    | (models.Q(invoice__isnull=True)
                       & models.Q(purchase_invoice__isnull=False))
                ),
                name="check_payment_invoice_reference",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["invoice"]),
            models.Index(fields=["purchase_invoice"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} ({self.status})"


class SalesSettings(TenantScopedModel):
    accounts_receivable = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    sales_revenue = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    vat_payable = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "sales_settings"
        verbose_name = "Sales Settings"
        verbose_name_plural = "Sales Settings"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="unique_sales_settings_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Sales settings (tenant {self.tenant_id})"