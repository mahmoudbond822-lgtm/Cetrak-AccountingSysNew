from decimal import Decimal

from django.db import transaction
from django.db import IntegrityError
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.inventory.models import Product, StockMovement
from apps.inventory.services import StockService, _quantize
from apps.purchases.models import (
    PurchaseInvoice,
    PurchaseInvoiceLine,
    PurchaseSettings,
    Vendor,
)
from apps.sales.services import compute_line_totals

_UNSET = object()


class PurchaseSettingsService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def get(self):
        obj, _ = PurchaseSettings.objects.get_or_create(tenant_id=self.tenant_id)
        return obj

    def update(self, **mappings):
        settings = self.get()
        for field, account in mappings.items():
            if account is None:
                setattr(settings, field, None)
                continue
            if not isinstance(account, Account):
                account = (
                    Account.objects.for_tenant(self.tenant_id)
                    .filter(pk=account)
                    .first()
                )
            if account is None:
                raise ValueError(f"{field} account does not exist.")
            expected_type = {
                "accounts_payable": "Liability",
                "expense_account": "Expense",
                "input_vat": "Asset",
            }[field]
            if account.type != expected_type:
                raise ValueError(
                    f"{field} account must be of type {expected_type}."
                )
            setattr(settings, field, account)
        settings.save()
        return settings


class PurchaseInvoiceService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def _list_invoices(self, status=None):
        qs = PurchaseInvoice.objects.for_tenant(self.tenant_id).select_related(
            "vendor"
        )
        if status:
            qs = qs.filter(status=status)
        return qs

    def _get_invoice(self, invoice_id):
        try:
            return PurchaseInvoice.objects.for_tenant(self.tenant_id).get(
                pk=invoice_id
            )
        except PurchaseInvoice.DoesNotExist:
            raise ValueError("Invoice not found.")

    def _compute_invoice_totals(self, lines_data, discount):
        subtotal = Decimal("0")
        tax = Decimal("0")
        for line in lines_data:
            quantity = Decimal(str(line.get("quantity", "0")))
            unit_price = Decimal(str(line.get("unit_price", "0")))
            tax_rate = Decimal(str(line.get("tax_rate", "0")))
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
            if unit_price < 0:
                raise ValueError("Unit price must not be negative.")
            if tax_rate < 0 or tax_rate > Decimal("100"):
                raise ValueError("Tax rate must be between 0 and 100.")
            line_subtotal, line_tax, _ = compute_line_totals(
                quantity, unit_price, tax_rate
            )
            subtotal += line_subtotal
            tax += line_tax
        discount = Decimal(str(discount or "0"))
        if discount < 0:
            raise ValueError("Discount must not be negative.")
        if discount > subtotal:
            raise ValueError("Discount cannot exceed the subtotal.")
        total = subtotal - discount + tax
        if total <= 0:
            raise ValueError("Invoice total must be greater than zero.")
        return subtotal, tax, total

    def _resolve_product(self, product_id):
        if product_id is None:
            return None
        if isinstance(product_id, Product):
            product = product_id
        else:
            try:
                product = Product.objects.for_tenant(self.tenant_id).get(
                    pk=product_id
                )
            except Product.DoesNotExist:
                raise ValueError("Product not found.")
        if product.tenant_id != self.tenant_id:
            raise ValueError("Product not found.")
        if not product.is_active:
            raise ValueError("Cannot use an inactive product.")
        return product

    def create_draft(self, *, number, vendor_id, invoice_date, due_date,
                     discount, notes, lines_data):
        if not lines_data:
            raise ValueError("An invoice must have at least one line.")
        try:
            vendor = Vendor.objects.for_tenant(self.tenant_id).get(pk=vendor_id)
        except Vendor.DoesNotExist:
            raise ValueError("Vendor not found.")
        if not vendor.is_active:
            raise ValueError("Cannot create an invoice for an inactive vendor.")
        subtotal, tax, total = self._compute_invoice_totals(lines_data, discount)
        try:
            with transaction.atomic():
                invoice = PurchaseInvoice.objects.create(
                    tenant_id=self.tenant_id,
                    number=number,
                    vendor=vendor,
                    invoice_date=invoice_date,
                    due_date=due_date or None,
                    status=PurchaseInvoice.Status.DRAFT,
                    notes=notes,
                    discount=discount or Decimal("0"),
                    subtotal=subtotal,
                    tax=tax,
                    total=total,
                )
                for line in lines_data:
                    line_subtotal, line_tax, line_total = compute_line_totals(
                        line.get("quantity"), line.get("unit_price"),
                        line.get("tax_rate"),
                    )
                    PurchaseInvoiceLine.objects.create(
                        invoice=invoice,
                        product=self._resolve_product(line.get("product_id")),
                        description=line["description"],
                        quantity=line.get("quantity"),
                        unit_price=line.get("unit_price"),
                        tax_rate=line.get("tax_rate", "0"),
                        subtotal=line_subtotal,
                        tax=line_tax,
                        total=line_total,
                    )
        except IntegrityError as exc:
            raise ValueError("Invoice number already exists.")
        return invoice

    def update_draft(self, invoice_id, *, number=None, vendor_id=None,
                     invoice_date=None, due_date=_UNSET, discount=None,
                     notes=_UNSET, lines_data=None):
        invoice = self._get_invoice(invoice_id)
        if invoice.status != PurchaseInvoice.Status.DRAFT:
            raise ValueError("Only draft purchase invoices can be edited.")
        if number is not None:
            invoice.number = number
        if vendor_id is not None:
            try:
                vendor = Vendor.objects.for_tenant(self.tenant_id).get(
                    pk=vendor_id
                )
            except Vendor.DoesNotExist:
                raise ValueError("Vendor not found.")
            if not vendor.is_active:
                raise ValueError("Cannot assign an inactive vendor.")
            invoice.vendor = vendor
        if invoice_date is not None:
            invoice.invoice_date = invoice_date
        if due_date is not _UNSET:
            invoice.due_date = due_date or None
        if (
            invoice.due_date
            and invoice.invoice_date
            and invoice.due_date < invoice.invoice_date
        ):
            raise ValueError("Due date cannot be before the invoice date.")
        if notes is not _UNSET:
            invoice.notes = notes
        if discount is not None:
            invoice.discount = discount
        if lines_data is not None:
            if not lines_data:
                raise ValueError("An invoice must have at least one line.")
            recompute_base = lines_data
        else:
            recompute_base = [
                {"quantity": line.quantity, "unit_price": line.unit_price,
                 "tax_rate": line.tax_rate}
                for line in invoice.lines.all()
            ]
        if not recompute_base:
            raise ValueError("An invoice must have at least one line.")
        subtotal, tax, total = self._compute_invoice_totals(
            recompute_base, invoice.discount
        )
        invoice.subtotal = subtotal
        invoice.tax = tax
        invoice.total = total
        try:
            with transaction.atomic():
                if lines_data is not None:
                    invoice.lines.all().delete()
                    for line in lines_data:
                        line_subtotal, line_tax, line_total = compute_line_totals(
                            line.get("quantity"), line.get("unit_price"),
                            line.get("tax_rate"),
                        )
                        PurchaseInvoiceLine.objects.create(
                            invoice=invoice,
                            product=self._resolve_product(
                                line.get("product_id")
                            ),
                            description=line["description"],
                            quantity=line.get("quantity"),
                            unit_price=line.get("unit_price"),
                            tax_rate=line.get("tax_rate", "0"),
                            subtotal=line_subtotal,
                            tax=line_tax,
                            total=line_total,
                        )
                invoice.save()
        except IntegrityError:
            raise ValueError("Invoice number already exists.")
        return invoice

    def post_invoice(self, invoice_id):
        invoice = self._get_invoice(invoice_id)
        if invoice.status != PurchaseInvoice.Status.DRAFT:
            raise ValueError("Only draft purchase invoices can be posted.")
        settings = PurchaseSettings.objects.for_tenant(self.tenant_id).first()
        if settings is None:
            raise ValueError("Purchase accounting settings are not configured.")
        if not settings.accounts_payable_id or not settings.expense_account_id:
            raise ValueError("Purchase accounting settings are not configured.")
        if invoice.tax > 0 and not settings.input_vat_id:
            raise ValueError("Purchase accounting settings are not configured.")
        ap_account = settings.accounts_payable
        expense_account = settings.expense_account
        vat_account = settings.input_vat if settings.input_vat_id else None
        if (
            ap_account.tenant_id != self.tenant_id
            or expense_account.tenant_id != self.tenant_id
        ):
            raise ValueError("Purchase accounting settings are invalid.")
        if (
            not ap_account.is_active
            or not expense_account.is_active
        ):
            raise ValueError("Purchase accounting settings are invalid.")
        if ap_account.type != "Liability":
            raise ValueError("Purchase accounting settings are invalid.")
        if expense_account.type != "Expense":
            raise ValueError("Purchase accounting settings are invalid.")
        if vat_account is not None:
            if (
                vat_account.tenant_id != self.tenant_id
                or not vat_account.is_active
            ):
                raise ValueError("Purchase accounting settings are invalid.")
            if vat_account.type != "Asset":
                raise ValueError("Purchase accounting settings are invalid.")
        reference = f"PUR-INV-{invoice.number}"
        vat_amount = invoice.tax
        lines = list(invoice.lines.select_related("product").order_by("pk"))
        stock_lines = [line for line in lines if line.product_id]
        stock = None
        inventory_account = None
        if stock_lines:
            stock = StockService(self.tenant_id)
            inv_settings, warehouse, inv_accounts = stock.validate_settings(
                "inventory_account"
            )
            inventory_account = inv_accounts["inventory_account"]
        try:
            with transaction.atomic():
                entry = JournalEntry.objects.create(
                    tenant_id=self.tenant_id,
                    date=invoice.invoice_date,
                    description=f"Purchase invoice {invoice.number}",
                    reference=reference,
                    posted=True,
                    posted_at=timezone.now(),
                )
                inventory_value = Decimal("0")
                if stock_lines:
                    subtotal = invoice.subtotal
                    discount = invoice.discount
                    nets = {}
                    for line in stock_lines:
                        allocated = Decimal("0")
                        if subtotal:
                            allocated = _quantize(
                                discount * Decimal(str(line.subtotal))
                                / subtotal
                            )
                        nets[line.id] = _quantize(
                            Decimal(str(line.subtotal)) - allocated
                        )
                    total_after_discount = subtotal - discount
                    inventory_value = sum(nets.values(), Decimal("0"))
                    if inventory_value > total_after_discount:
                        surplus = inventory_value - total_after_discount
                        inventory_value = total_after_discount
                        last_id = list(nets.keys())[-1]
                        nets[last_id] = nets[last_id] - surplus
                    stock_lines.sort(key=lambda line: line.product_id)
                    for line in stock_lines:
                        net = nets[line.id]
                        balance = stock._get_balance(
                            line.product_id, warehouse.id
                        )
                        unit_cost = _quantize(
                            net / Decimal(str(line.quantity))
                        )
                        stock.receive(
                            balance,
                            line.quantity,
                            unit_cost,
                            StockMovement.MovementType.RECEIPT,
                            purchase_invoice=invoice,
                            value=net,
                        )
                    if inventory_value > 0:
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=inventory_account,
                            debit=inventory_value,
                            credit=0,
                            description=(
                                f"Inventory for purchase invoice "
                                f"{invoice.number}"
                            ),
                        )
                expense_value = (
                    invoice.subtotal - invoice.discount - inventory_value
                )
                if expense_value > 0:
                    JournalEntryLine.objects.create(
                        entry=entry,
                        account=expense_account,
                        debit=expense_value,
                        credit=0,
                        description=(
                            f"Expense for purchase invoice {invoice.number}"
                        ),
                    )
                if vat_amount > 0:
                    JournalEntryLine.objects.create(
                        entry=entry,
                        account=vat_account,
                        debit=vat_amount,
                        credit=0,
                        description=(
                            f"Input VAT for purchase invoice {invoice.number}"
                        ),
                    )
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=ap_account,
                    debit=0,
                    credit=invoice.total,
                    description=(
                        f"Accounts payable for purchase invoice {invoice.number}"
                    ),
                )
                invoice.posted_journal = entry
                invoice.status = PurchaseInvoice.Status.POSTED
                invoice.posted_at = timezone.now()
                invoice.save(update_fields=[
                    "posted_journal", "status", "posted_at", "updated_at",
                ])
        except IntegrityError:
            raise ValueError("Journal entry reference already exists.")
        return invoice

    def delete_invoice(self, invoice_id):
        invoice = self._get_invoice(invoice_id)
        if invoice.status != PurchaseInvoice.Status.DRAFT:
            raise ValueError("Only draft purchase invoices can be deleted.")
        invoice.delete()