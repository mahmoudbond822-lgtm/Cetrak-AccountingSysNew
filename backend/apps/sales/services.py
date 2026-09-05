from decimal import Decimal

from django.db import transaction
from django.db import IntegrityError
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, SalesSettings

_UNSET = object()


class SalesSettingsService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def get(self):
        obj, _ = SalesSettings.objects.get_or_create(tenant_id=self.tenant_id)
        return obj

    def update(self, **mappings):
        settings = self.get()
        for field, account in mappings.items():
            if account is None:
                setattr(settings, field, None)
                continue
            if not isinstance(account, Account):
                account = (
                    Account.objects.for_tenant(self.tenant_id).filter(pk=account).first()
                )
            if account is None:
                raise ValueError(f"{field} account does not exist.")
            expected_type = {
                "accounts_receivable": "Asset",
                "sales_revenue": "Revenue",
                "vat_payable": "Liability",
            }[field]
            if account.type != expected_type:
                raise ValueError(
                    f"{field} account must be of type {expected_type}."
                )
            setattr(settings, field, account)
        settings.save()
        return settings


def compute_line_totals(quantity, unit_price, tax_rate):
    quantity_q = Decimal(quantity)
    unit_price_q = Decimal(unit_price)
    tax_rate_q = Decimal(tax_rate or "0")
    subtotal = quantity_q * unit_price_q
    tax = subtotal * tax_rate_q / Decimal("100")
    total = subtotal + tax
    return subtotal, tax, total


class SalesInvoiceService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def _list_invoices(self, status=None):
        qs = SalesInvoice.objects.for_tenant(self.tenant_id).select_related("customer")
        if status:
            qs = qs.filter(status=status)
        return qs

    def _get_invoice(self, invoice_id):
        try:
            return SalesInvoice.objects.for_tenant(self.tenant_id).get(pk=invoice_id)
        except SalesInvoice.DoesNotExist:
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

    def create_draft(self, *, number, customer_id, invoice_date, due_date,
                     discount, notes, lines_data):
        if not lines_data:
            raise ValueError("An invoice must have at least one line.")
        try:
            customer = Customer.objects.for_tenant(self.tenant_id).get(pk=customer_id)
        except Customer.DoesNotExist:
            raise ValueError("Customer not found.")
        if not customer.is_active:
            raise ValueError("Cannot create an invoice for an inactive customer.")
        subtotal, tax, total = self._compute_invoice_totals(lines_data, discount)
        try:
            with transaction.atomic():
                invoice = SalesInvoice.objects.create(
                    tenant_id=self.tenant_id,
                    number=number,
                    customer=customer,
                    invoice_date=invoice_date,
                    due_date=due_date or None,
                    status=SalesInvoice.Status.DRAFT,
                    notes=notes,
                    discount=discount or Decimal("0"),
                    subtotal=subtotal,
                    tax=tax,
                    total=total,
                )
                for line in lines_data:
                    line_subtotal, line_tax, line_total = compute_line_totals(
                        line.get("quantity"), line.get("unit_price"), line.get("tax_rate")
                    )
                    SalesInvoiceLine.objects.create(
                        invoice=invoice,
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

    def update_draft(self, invoice_id, *, number=None, customer_id=None,
                     invoice_date=None, due_date=_UNSET, discount=None,
                     notes=_UNSET, lines_data=None):
        invoice = self._get_invoice(invoice_id)
        if invoice.status != SalesInvoice.Status.DRAFT:
            raise ValueError("Only draft invoices can be edited.")
        if number is not None:
            invoice.number = number
        if customer_id is not None:
            try:
                customer = Customer.objects.for_tenant(self.tenant_id).get(
                    pk=customer_id
                )
            except Customer.DoesNotExist:
                raise ValueError("Customer not found.")
            if not customer.is_active:
                raise ValueError("Cannot assign an inactive customer.")
            invoice.customer = customer
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
                        SalesInvoiceLine.objects.create(
                            invoice=invoice,
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
        if invoice.status != SalesInvoice.Status.DRAFT:
            raise ValueError("Only draft invoices can be posted.")
        settings = SalesSettings.objects.for_tenant(self.tenant_id).first()
        if settings is None:
            raise ValueError("Sales accounting settings are not configured.")
        if not settings.accounts_receivable_id or not settings.sales_revenue_id:
            raise ValueError("Sales accounting settings are not configured.")
        ar_account = settings.accounts_receivable
        revenue_account = settings.sales_revenue
        if (
            ar_account.tenant_id != self.tenant_id
            or revenue_account.tenant_id != self.tenant_id
        ):
            raise ValueError("Sales accounting settings are invalid.")
        if not ar_account.is_active or not revenue_account.is_active:
            raise ValueError("Sales accounting settings are invalid.")
        vat_account = settings.vat_payable if settings.vat_payable_id else None
        if vat_account is not None and (
            not vat_account.is_active or vat_account.tenant_id != self.tenant_id
        ):
            raise ValueError("Sales accounting settings are invalid.")
        reference = f"SALES-INV-{invoice.number}"
        vat_amount = invoice.tax
        try:
            with transaction.atomic():
                entry = JournalEntry.objects.create(
                    tenant_id=self.tenant_id,
                    date=invoice.invoice_date,
                    description=f"Sales invoice {invoice.number}",
                    reference=reference,
                    posted=True,
                    posted_at=timezone.now(),
                )
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=ar_account,
                    debit=invoice.total,
                    credit=0,
                    description=f"Accounts receivable for invoice {invoice.number}",
                )
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=revenue_account,
                    debit=0,
                    credit=invoice.subtotal - invoice.discount,
                    description=f"Revenue for invoice {invoice.number}",
                )
                if vat_amount > 0:
                    JournalEntryLine.objects.create(
                        entry=entry,
                        account=vat_account,
                        debit=0,
                        credit=vat_amount,
                        description=f"VAT for invoice {invoice.number}",
                    )
                invoice.posted_journal = entry
                invoice.status = SalesInvoice.Status.POSTED
                invoice.posted_at = timezone.now()
                invoice.save(update_fields=[
                    "posted_journal", "status", "posted_at", "updated_at",
                ])
        except IntegrityError:
            raise ValueError("Journal entry reference already exists.")
        return invoice

    def delete_invoice(self, invoice_id):
        invoice = self._get_invoice(invoice_id)
        if invoice.status != SalesInvoice.Status.DRAFT:
            raise ValueError("Only draft invoices can be deleted.")
        invoice.delete()