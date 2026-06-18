from django.db import models
from django.core.exceptions import ValidationError

from apps.core.models import TenantScopedModel, BaseModel


class Account(TenantScopedModel):
    class Type(models.TextChoices):
        ASSET = "Asset", "Asset"
        LIABILITY = "Liability", "Liability"
        EQUITY = "Equity", "Equity"
        REVENUE = "Revenue", "Revenue"
        EXPENSE = "Expense", "Expense"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_account"
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self):
        return f"{self.name} ({self.type})"


class JournalEntry(TenantScopedModel):
    date = models.DateField()
    description = models.TextField()
    reference = models.CharField(max_length=255)
    posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounting_journalentry"
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "reference"],
                name="unique_reference_per_tenant",
            ),
        ]

    def __str__(self):
        return f"JE {self.reference} @ {self.date}"

    @property
    def total_debit(self):
        return self.lines.aggregate(total=models.Sum("debit"))["total"] or 0

    @property
    def total_credit(self):
        return self.lines.aggregate(total=models.Sum("credit"))["total"] or 0

    @property
    def is_balanced(self):
        return abs(self.total_debit - self.total_credit) < 0.01

    def post_entry(self):
        from django.utils import timezone
        self.posted = True
        self.posted_at = timezone.now()
        self.save()

    def clean(self):
        if not self.is_balanced:
            raise ValidationError(
                f"Journal entry is not balanced. "
                f"Total debits ({self.total_debit}) do not equal "
                f"total credits ({self.total_credit})."
            )


class JournalEntryLine(BaseModel):
    entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="lines"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="journal_lines"
    )
    debit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    credit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "accounting_journalentryline"
        verbose_name = "Journal Entry Line"
        verbose_name_plural = "Journal Entry Lines"

    def __str__(self):
        direction = f"Dr {self.debit}" if self.debit else f"Cr {self.credit}"
        return f"{self.account.name}: {direction}"

    def clean(self):
        if self.debit and self.credit:
            raise ValidationError(
                "A line cannot have both debit and credit amounts."
            )
        if self.debit < 0 or self.credit < 0:
            raise ValidationError("Amounts must be non-negative.")
