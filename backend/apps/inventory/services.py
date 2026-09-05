from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db import IntegrityError
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.inventory.models import (
    InventorySettings,
    Product,
    StockAdjustment,
    StockAdjustmentLine,
    StockBalance,
    StockMovement,
    Warehouse,
)

_UNSET = object()

_DECIMAL_4 = Decimal("0.0001")


def _quantize(value):
    return Decimal(value).quantize(_DECIMAL_4, rounding=ROUND_HALF_UP)


class InventorySettingsService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def get(self):
        with transaction.atomic():
            settings, _ = InventorySettings.objects.get_or_create(
                tenant_id=self.tenant_id
            )
            if settings.default_warehouse_id is None:
                warehouse, _ = Warehouse.objects.get_or_create(
                    tenant_id=self.tenant_id,
                    name="Default",
                    defaults={"is_active": True},
                )
                settings.default_warehouse = warehouse
                settings.save(update_fields=["default_warehouse", "updated_at"])
        return settings

    def update(self, **mappings):
        settings = self.get()
        for field, value in mappings.items():
            if field == "default_warehouse":
                if value is None:
                    settings.default_warehouse = None
                    continue
                if isinstance(value, Warehouse):
                    value = value.pk
                value = (
                    Warehouse.objects.for_tenant(self.tenant_id)
                    .filter(pk=value)
                    .first()
                )
                if value is None:
                    raise ValueError("Warehouse not found.")
                if not value.is_active:
                    raise ValueError("Warehouse is inactive.")
                settings.default_warehouse = value
                continue
            if value is None:
                setattr(settings, field, None)
                continue
            if not isinstance(value, Account):
                value = (
                    Account.objects.for_tenant(self.tenant_id)
                    .filter(pk=value)
                    .first()
                )
            if value is None:
                raise ValueError(f"{field} account does not exist.")
            expected_type = {
                "inventory_account": "Asset",
                "cogs_account": "Expense",
                "adjustments_account": "Expense",
            }[field]
            if value.type != expected_type:
                raise ValueError(
                    f"{field} account must be of type {expected_type}."
                )
            setattr(settings, field, value)
        settings.save()
        return settings


class StockService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def get_settings(self):
        return InventorySettingsService(self.tenant_id).get()

    def validate_settings(self, *required_fields):
        """Return a validated (settings, warehouse, accounts) bundle or raise.

        required_fields is a subset of
        ('inventory_account', 'cogs_account', 'adjustments_account').
        All lookups are tenant-scoped; every check is re-run at posting time
        inside the calling transaction (row locks happen after this).
        """
        settings = self.get_settings()
        for field in required_fields:
            if not getattr(settings, f"{field}_id"):
                raise ValueError(
                    "Inventory accounting settings are not configured."
                )
        warehouse = settings.default_warehouse
        if warehouse is None or not warehouse.is_active:
            raise ValueError("Inventory accounting settings are not configured.")
        if warehouse.tenant_id != self.tenant_id:
            raise ValueError("Inventory accounting settings are invalid.")
        accounts = {}
        for field in required_fields:
            account = getattr(settings, field)
            if (
                account.tenant_id != self.tenant_id
                or not account.is_active
            ):
                raise ValueError("Inventory accounting settings are invalid.")
            accounts[field] = account
        return settings, warehouse, accounts

    def allocate_line_nets(self, lines, discount):
        """Return per-line net (Quantized) after proportional discount.

        Sum of returned nets may differ from subtotal - discount by at most a
        fraction of a cent; the residual is absorbed by the expense leg at
        posting so the Journal Entry always balances exactly.
        """
        subtotal = sum(
            (Decimal(str(getattr(line, "subtotal", line.get("subtotal", "0"))))
             for line in lines),
            Decimal("0"),
        )
        discount = Decimal(str(discount or "0"))
        nets = []
        for line in lines:
            line_subtotal = Decimal(
                str(getattr(line, "subtotal", line.get("subtotal", "0")))
            )
            allocated = Decimal("0")
            if subtotal:
                allocated = _quantize(
                    discount * line_subtotal / subtotal
                )
            nets.append(_quantize(line_subtotal - allocated))
        return nets

    def _get_balance(self, product_id, warehouse_id, create=True):
        balance = (
            StockBalance.objects.select_for_update()
            .filter(
                tenant_id=self.tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
            )
            .first()
        )
        if balance is None and create:
            try:
                balance = StockBalance.objects.create(
                    tenant_id=self.tenant_id,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=Decimal("0"),
                    value=Decimal("0"),
                    moving_avg_cost=Decimal("0"),
                )
            except IntegrityError:
                balance = (
                    StockBalance.objects.select_for_update()
                    .get(
                        tenant_id=self.tenant_id,
                        product_id=product_id,
                        warehouse_id=warehouse_id,
                    )
                )
        return balance

    def receive(self, balance, quantity, unit_cost, movement_type, *,
                value=None, **source):
        """Increase stock at the given unit cost; updates weighted average."""
        quantity = Decimal(str(quantity))
        unit_cost = Decimal(str(unit_cost))
        value_change = (
            Decimal(str(value))
            if value is not None
            else _quantize(quantity * unit_cost)
        )
        new_value = balance.value + value_change
        new_quantity = balance.quantity + quantity
        new_avg = (
            _quantize(new_value / new_quantity)
            if new_quantity
            else Decimal("0")
        )
        balance.quantity = new_quantity
        balance.value = new_value
        balance.moving_avg_cost = new_avg
        balance.save(update_fields=[
            "quantity", "value", "moving_avg_cost", "updated_at",
        ])
        StockMovement.objects.create(
            tenant_id=self.tenant_id,
            product_id=balance.product_id,
            warehouse_id=balance.warehouse_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            value=value_change,
            **source,
        )
        return balance

    def issue(self, balance, quantity, movement_type, **source):
        """Remove stock at current weighted average; returns consumed value.

        Raises ValueError if the balance cannot satisfy the quantity
        (negative stock is hard-rejected).
        """
        quantity = Decimal(str(quantity))
        if quantity > balance.quantity:
            raise ValueError("Insufficient stock.")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        avg = balance.moving_avg_cost
        value_change = _quantize(quantity * avg)
        new_value = balance.value - value_change
        new_quantity = balance.quantity - quantity
        new_avg = (
            _quantize(new_value / new_quantity)
            if new_quantity
            else Decimal("0")
        )
        balance.quantity = new_quantity
        balance.value = new_value
        balance.moving_avg_cost = new_avg
        balance.save(update_fields=[
            "quantity", "value", "moving_avg_cost", "updated_at",
        ])
        StockMovement.objects.create(
            tenant_id=self.tenant_id,
            product_id=balance.product_id,
            warehouse_id=balance.warehouse_id,
            movement_type=movement_type,
            quantity=-quantity,
            unit_cost=avg,
            value=-value_change,
            **source,
        )
        return value_change


class StockAdjustmentService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def _get_adjustment(self, adjustment_id):
        try:
            return StockAdjustment.objects.for_tenant(self.tenant_id).get(
                pk=adjustment_id
            )
        except StockAdjustment.DoesNotExist:
            raise ValueError("Adjustment not found.")

    def _get_product(self, product_id):
        try:
            return (
                Product.objects.for_tenant(self.tenant_id).get(pk=product_id)
            )
        except Product.DoesNotExist:
            raise ValueError("Product not found.")

    def create_draft(self, *, number, adjustment_date, reason, lines_data,
                     notes=None):
        if not lines_data:
            raise ValueError("An adjustment must have at least one line.")
        validated_lines = []
        for line in lines_data:
            quantity = Decimal(str(line.get("quantity", "0")))
            if quantity == 0:
                raise ValueError("Adjustment quantity must not be zero.")
            product = self._get_product(line["product_id"])
            validated_lines.append((product, quantity))
        try:
            with transaction.atomic():
                adjustment = StockAdjustment.objects.create(
                    tenant_id=self.tenant_id,
                    number=number,
                    adjustment_date=adjustment_date,
                    reason=reason,
                    notes=notes,
                    status=StockAdjustment.Status.DRAFT,
                )
                for product, quantity in validated_lines:
                    StockAdjustmentLine.objects.create(
                        adjustment=adjustment,
                        product=product,
                        quantity=quantity,
                    )
        except IntegrityError:
            raise ValueError("Adjustment number already exists.")
        return adjustment

    def update_draft(self, adjustment_id, *, number=None,
                     adjustment_date=None, reason=None, notes=_UNSET,
                     lines_data=None):
        adjustment = self._get_adjustment(adjustment_id)
        if adjustment.status != StockAdjustment.Status.DRAFT:
            raise ValueError("Only draft adjustments can be edited.")
        if number is not None:
            adjustment.number = number
        if adjustment_date is not None:
            adjustment.adjustment_date = adjustment_date
        if reason is not None:
            adjustment.reason = reason
        if notes is not _UNSET:
            adjustment.notes = notes or None
        if lines_data is not None:
            if not lines_data:
                raise ValueError("An adjustment must have at least one line.")
            validated_lines = []
            for line in lines_data:
                quantity = Decimal(str(line.get("quantity", "0")))
                if quantity == 0:
                    raise ValueError("Adjustment quantity must not be zero.")
                product = self._get_product(line["product_id"])
                validated_lines.append((product, quantity))
            try:
                with transaction.atomic():
                    adjustment.lines.all().delete()
                    for product, quantity in validated_lines:
                        StockAdjustmentLine.objects.create(
                            adjustment=adjustment,
                            product=product,
                            quantity=quantity,
                        )
                    adjustment.save()
            except IntegrityError:
                raise ValueError("Adjustment number already exists.")
        else:
            try:
                with transaction.atomic():
                    adjustment.save()
            except IntegrityError:
                raise ValueError("Adjustment number already exists.")
        return adjustment

    def delete_draft(self, adjustment_id):
        adjustment = self._get_adjustment(adjustment_id)
        if adjustment.status != StockAdjustment.Status.DRAFT:
            raise ValueError("Only draft adjustments can be deleted.")
        adjustment.delete()

    def post_adjustment(self, adjustment_id):
        adjustment = self._get_adjustment(adjustment_id)
        if adjustment.status != StockAdjustment.Status.DRAFT:
            raise ValueError("Only draft adjustments can be posted.")
        stock = StockService(self.tenant_id)
        settings, warehouse, accounts = stock.validate_settings(
            "inventory_account", "adjustments_account"
        )
        inventory_account = accounts["inventory_account"]
        adjustments_account = accounts["adjustments_account"]
        reference = f"ADJ-INV-{adjustment.number}"
        line_rows = list(
            adjustment.lines.select_related("product").order_by("product_id")
        )
        try:
            with transaction.atomic():
                entry = JournalEntry.objects.create(
                    tenant_id=self.tenant_id,
                    date=adjustment.adjustment_date,
                    description=f"Stock adjustment {adjustment.number}",
                    reference=reference,
                    posted=True,
                    posted_at=timezone.now(),
                )
                for line in line_rows:
                    balance = stock._get_balance(
                        line.product_id, warehouse.id
                    )
                    quantity = Decimal(str(line.quantity))
                    if quantity > 0:
                        unit_cost = balance.moving_avg_cost
                        value = _quantize(quantity * unit_cost)
                        stock.receive(
                            balance,
                            quantity,
                            unit_cost,
                            StockMovement.MovementType.ADJUSTMENT,
                            adjustment=adjustment,
                        )
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=inventory_account,
                            debit=value,
                            credit=0,
                            description=(
                                f"Inventory for adjustment {adjustment.number}"
                            ),
                        )
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=adjustments_account,
                            debit=0,
                            credit=value,
                            description=(
                                f"Stock adjustments for {adjustment.number}"
                            ),
                        )
                    else:
                        out_quantity = -quantity
                        value = stock.issue(
                            balance,
                            out_quantity,
                            StockMovement.MovementType.ADJUSTMENT,
                            adjustment=adjustment,
                        )
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=adjustments_account,
                            debit=value,
                            credit=0,
                            description=(
                                f"Stock adjustments for {adjustment.number}"
                            ),
                        )
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=inventory_account,
                            debit=0,
                            credit=value,
                            description=(
                                f"Inventory for adjustment {adjustment.number}"
                            ),
                        )
                adjustment.posted_journal = entry
                adjustment.status = StockAdjustment.Status.POSTED
                adjustment.posted_at = timezone.now()
                adjustment.save(update_fields=[
                    "posted_journal", "status", "posted_at", "updated_at",
                ])
        except IntegrityError:
            raise ValueError("Journal entry reference already exists.")
        return adjustment