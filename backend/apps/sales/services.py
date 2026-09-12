from decimal import Decimal

from django.db import transaction
from django.db import IntegrityError
from django.db.models import Sum
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalEntryLine
from apps.core.audit import AuditService
from apps.inventory.models import Product, StockMovement
from apps.inventory.services import StockService
from apps.purchases.models import PurchaseInvoice, PurchaseSettings
from apps.sales.models import (
    Customer,
    Payment,
    SalesInvoice,
    SalesInvoiceLine,
    SalesSettings,
)

_UNSET = object()


class SalesSettingsService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def get(self):
        obj, _ = SalesSettings.objects.get_or_create(tenant_id=self.tenant_id)
        return obj

    def update(self, **mappings):
        settings = self.get()
        before = {
            "accounts_receivable_id": str(settings.accounts_receivable_id) if settings.accounts_receivable_id else None,
            "sales_revenue_id": str(settings.sales_revenue_id) if settings.sales_revenue_id else None,
            "vat_payable_id": str(settings.vat_payable_id) if settings.vat_payable_id else None,
        }
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
        AuditService.record(
            action="settings.sales.update",
            tenant_id=self.tenant_id,
            target=settings,
            before=before,
            after={
                "accounts_receivable_id": str(settings.accounts_receivable_id) if settings.accounts_receivable_id else None,
                "sales_revenue_id": str(settings.sales_revenue_id) if settings.sales_revenue_id else None,
                "vat_payable_id": str(settings.vat_payable_id) if settings.vat_payable_id else None,
            },
        )
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
        AuditService.record(
            action="sales.invoice.create",
            tenant_id=self.tenant_id,
            target=invoice,
            after={
                "number": invoice.number,
                "customer_id": str(invoice.customer_id),
                "status": invoice.status,
                "invoice_date": str(invoice.invoice_date),
                "due_date": str(invoice.due_date) if invoice.due_date else None,
                "discount": str(invoice.discount),
                "subtotal": str(invoice.subtotal),
                "tax": str(invoice.tax),
                "total": str(invoice.total),
            },
        )
        return invoice

    def update_draft(self, invoice_id, *, number=None, customer_id=None,
                     invoice_date=None, due_date=_UNSET, discount=None,
                     notes=_UNSET, lines_data=None):
        invoice = self._get_invoice(invoice_id)
        before = {
            "number": invoice.number,
            "customer_id": str(invoice.customer_id),
            "status": invoice.status,
            "subtotal": str(invoice.subtotal),
            "tax": str(invoice.tax),
            "total": str(invoice.total),
        }
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
        AuditService.record(
            action="sales.invoice.update",
            tenant_id=self.tenant_id,
            target=invoice,
            before=before,
            after={
                "number": invoice.number,
                "customer_id": str(invoice.customer_id),
                "status": invoice.status,
                "discount": str(invoice.discount),
                "subtotal": str(invoice.subtotal),
                "tax": str(invoice.tax),
                "total": str(invoice.total),
            },
        )
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
        stock_lines = [
            line
            for line in invoice.lines.select_related("product").order_by("pk")
            if line.product_id
        ]
        stock = None
        cogs_account = None
        inventory_account = None
        if stock_lines:
            stock = StockService(self.tenant_id)
            inv_settings, warehouse, inv_accounts = stock.validate_settings(
                "inventory_account", "cogs_account"
            )
            cogs_account = inv_accounts["cogs_account"]
            inventory_account = inv_accounts["inventory_account"]
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
                if stock_lines:
                    stock_lines.sort(key=lambda line: line.product_id)
                    for line in stock_lines:
                        balance = stock._get_balance(
                            line.product_id, warehouse.id
                        )
                        consumed = stock.issue(
                            balance,
                            line.quantity,
                            StockMovement.MovementType.ISSUE,
                            sales_invoice=invoice,
                        )
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=cogs_account,
                            debit=consumed,
                            credit=0,
                            description=(
                                f"Cost of goods sold for invoice "
                                f"{invoice.number}"
                            ),
                        )
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=inventory_account,
                            debit=0,
                            credit=consumed,
                            description=(
                                f"Inventory for invoice {invoice.number}"
                            ),
                        )
                invoice.posted_journal = entry
                invoice.status = SalesInvoice.Status.POSTED
                invoice.posted_at = timezone.now()
                invoice.save(update_fields=[
                    "posted_journal", "status", "posted_at", "updated_at",
                ])
                AuditService.record(
                    action="sales.invoice.post",
                    tenant_id=self.tenant_id,
                    target=invoice,
                    before={"status": SalesInvoice.Status.DRAFT},
                    after={
                        "status": SalesInvoice.Status.POSTED,
                        "number": invoice.number,
                        "total": str(invoice.total),
                        "journal_reference": reference,
                    },
                )
        except IntegrityError:
            raise ValueError("Journal entry reference already exists.")
        return invoice

    def delete_invoice(self, invoice_id):
        invoice = self._get_invoice(invoice_id)
        if invoice.status != SalesInvoice.Status.DRAFT:
            raise ValueError("Only draft invoices can be deleted.")
        before = {
            "number": invoice.number,
            "customer_id": str(invoice.customer_id),
            "status": invoice.status,
            "total": str(invoice.total),
        }
        invoice.delete()
        AuditService.record(
            action="sales.invoice.delete",
            tenant_id=self.tenant_id,
            target=invoice,
            before=before,
        )


class PaymentService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def _get_payment(self, payment_id):
        try:
            return Payment.objects.for_tenant(self.tenant_id).get(pk=payment_id)
        except Payment.DoesNotExist:
            raise ValueError("Payment not found.")

    def _get_invoice(self, invoice_id):
        try:
            return SalesInvoice.objects.for_tenant(self.tenant_id).get(pk=invoice_id)
        except SalesInvoice.DoesNotExist:
            raise ValueError("Invoice not found.")

    def _get_purchase_invoice(self, purchase_invoice_id):
        try:
            return PurchaseInvoice.objects.for_tenant(self.tenant_id).get(
                pk=purchase_invoice_id
            )
        except PurchaseInvoice.DoesNotExist:
            raise ValueError("Invoice not found.")

    def _get_cash_account(self, account):
        if not isinstance(account, Account):
            account = (
                Account.objects.for_tenant(self.tenant_id).filter(pk=account).first()
            )
        if account is None:
            raise ValueError("Cash account not found.")
        if account.tenant_id != self.tenant_id:
            raise ValueError("Cash account is invalid.")
        if not account.is_active:
            raise ValueError("Cash account is invalid.")
        if account.type != "Asset":
            raise ValueError("Cash account must be of type Asset.")
        return account

    def invoice_paid_amount(self, invoice):
        paid = (
            Payment.objects.for_tenant(self.tenant_id)
            .filter(invoice=invoice, status=Payment.Status.POSTED)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        return Decimal(paid)

    def invoice_outstanding(self, invoice):
        return max(invoice.total - self.invoice_paid_amount(invoice), Decimal("0"))

    def purchase_paid_amount(self, purchase_invoice):
        paid = (
            Payment.objects.for_tenant(self.tenant_id)
            .filter(
                purchase_invoice=purchase_invoice,
                direction=Payment.Direction.PAYABLE,
                status=Payment.Status.POSTED,
            )
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        return Decimal(paid)

    def purchase_outstanding(self, purchase_invoice):
        return max(
            purchase_invoice.total
            - self.purchase_paid_amount(purchase_invoice),
            Decimal("0"),
        )

    def create_draft(self, *, number, payment_date, amount=None, method,
                     cash_account, reference=None, notes=None,
                     direction=Payment.Direction.RECEIVABLE,
                     invoice_id=None, purchase_invoice_id=None):
        if direction == Payment.Direction.PAYABLE:
            invoice = self._get_purchase_invoice(purchase_invoice_id)
            if invoice.status != PurchaseInvoice.Status.POSTED:
                raise ValueError("Only posted purchase invoices can be paid.")
            outstanding = self.purchase_outstanding(invoice)
        else:
            invoice = self._get_invoice(invoice_id)
            if invoice.status != SalesInvoice.Status.POSTED:
                raise ValueError("Only posted invoices can receive payments.")
            outstanding = self.invoice_outstanding(invoice)
        if amount is None:
            amount = outstanding
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if amount > outstanding:
            raise ValueError("Amount exceeds the outstanding balance.")
        account = self._get_cash_account(cash_account)
        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    tenant_id=self.tenant_id,
                    number=number,
                    direction=direction,
                    invoice=(
                        invoice if direction == Payment.Direction.RECEIVABLE else None
                    ),
                    purchase_invoice=(
                        invoice if direction == Payment.Direction.PAYABLE else None
                    ),
                    payment_date=payment_date,
                    amount=amount,
                    method=method,
                    cash_account=account,
                    reference=reference or None,
                    notes=notes or None,
                    status=Payment.Status.DRAFT,
                )
        except IntegrityError:
            raise ValueError("Payment number already exists.")
        AuditService.record(
            action="payment.create",
            tenant_id=self.tenant_id,
            target=payment,
            after={
                "number": payment.number,
                "direction": payment.direction,
                "invoice_id": payment.invoice_id,
                "purchase_invoice_id": payment.purchase_invoice_id,
                "amount": str(payment.amount),
                "method": payment.method,
                "status": payment.status,
            },
        )
        return payment

    def update_draft(self, payment_id, *, number=None, invoice_id=None,
                     purchase_invoice_id=None, payment_date=None, amount=None,
                     method=None, cash_account=None, reference=_UNSET,
                     notes=_UNSET):
        payment = self._get_payment(payment_id)
        before = {
            "number": payment.number,
            "amount": str(payment.amount),
            "method": payment.method,
            "status": payment.status,
        }
        if payment.status != Payment.Status.DRAFT:
            raise ValueError("Only draft payments can be edited.")
        if number is not None:
            payment.number = number
        if payment.direction == Payment.Direction.RECEIVABLE:
            if invoice_id is not None:
                invoice = self._get_invoice(invoice_id)
                if invoice.status != SalesInvoice.Status.POSTED:
                    raise ValueError("Only posted invoices can receive payments.")
                payment.invoice = invoice
        else:
            if purchase_invoice_id is not None:
                invoice = self._get_purchase_invoice(purchase_invoice_id)
                if invoice.status != PurchaseInvoice.Status.POSTED:
                    raise ValueError("Only posted purchase invoices can be paid.")
                payment.purchase_invoice = invoice
        if payment_date is not None:
            payment.payment_date = payment_date
        if amount is not None:
            payment.amount = amount
        if method is not None:
            payment.method = method
        if cash_account is not None:
            payment.cash_account = self._get_cash_account(cash_account)
        if reference is not _UNSET:
            payment.reference = reference or None
        if notes is not _UNSET:
            payment.notes = notes or None
        final_amount = Decimal(str(payment.amount))
        if final_amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if payment.direction == Payment.Direction.RECEIVABLE:
            outstanding = self.invoice_outstanding(payment.invoice)
        else:
            outstanding = self.purchase_outstanding(payment.purchase_invoice)
        if final_amount > outstanding:
            raise ValueError("Amount exceeds the outstanding balance.")
        try:
            with transaction.atomic():
                payment.save()
        except IntegrityError:
            raise ValueError("Payment number already exists.")
        AuditService.record(
            action="payment.update",
            tenant_id=self.tenant_id,
            target=payment,
            before=before,
            after={
                "number": payment.number,
                "amount": str(payment.amount),
                "method": payment.method,
                "status": payment.status,
            },
        )
        return payment

    def delete_draft(self, payment_id):
        payment = self._get_payment(payment_id)
        if payment.status != Payment.Status.DRAFT:
            raise ValueError("Only draft payments can be deleted.")
        before = {
            "number": payment.number,
            "amount": str(payment.amount),
            "status": payment.status,
        }
        payment.delete()
        AuditService.record(
            action="payment.delete",
            tenant_id=self.tenant_id,
            target=payment,
            before=before,
        )

    def post_payment(self, payment_id):
        payment = self._get_payment(payment_id)
        if payment.status != Payment.Status.DRAFT:
            raise ValueError("Payment is already posted.")
        if payment.direction == Payment.Direction.PAYABLE:
            return self._post_payable(payment)
        return self._post_receivable(payment)

    def _post_receivable(self, payment):
        settings = SalesSettings.objects.for_tenant(self.tenant_id).first()
        if settings is None or not settings.accounts_receivable_id:
            raise ValueError("Sales accounting settings are not configured.")
        ar_account = settings.accounts_receivable
        if (
            ar_account.tenant_id != self.tenant_id
            or not ar_account.is_active
            or ar_account.type != "Asset"
        ):
            raise ValueError("Sales accounting settings are not configured.")
        try:
            with transaction.atomic():
                invoice = (
                    SalesInvoice.objects.for_tenant(self.tenant_id)
                    .select_for_update()
                    .get(pk=payment.invoice_id)
                )
                if invoice.status != SalesInvoice.Status.POSTED:
                    raise ValueError("Invoice is not posted.")
                amount = Decimal(str(payment.amount))
                if amount <= 0:
                    raise ValueError("Amount must be greater than zero.")
                if amount > self.invoice_outstanding(invoice):
                    raise ValueError("Amount exceeds the outstanding balance.")
                reference = f"PAY-INV-{invoice.number}-{payment.number}"
                entry = JournalEntry.objects.create(
                    tenant_id=self.tenant_id,
                    date=payment.payment_date,
                    description=f"Payment {payment.number} for invoice {invoice.number}",
                    reference=reference,
                    posted=True,
                    posted_at=timezone.now(),
                )
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=payment.cash_account,
                    debit=amount,
                    credit=0,
                    description=f"Cash received for invoice {invoice.number}",
                )
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=ar_account,
                    debit=0,
                    credit=amount,
                    description=f"Accounts receivable for invoice {invoice.number}",
                )
                payment.journal_entry = entry
                payment.status = Payment.Status.POSTED
                payment.posted_at = timezone.now()
                payment.save(update_fields=[
                    "journal_entry", "status", "posted_at", "updated_at",
                ])
                AuditService.record(
                    action="payment.post",
                    tenant_id=self.tenant_id,
                    target=payment,
                    before={"status": Payment.Status.DRAFT},
                    after={
                        "status": Payment.Status.POSTED,
                        "number": payment.number,
                        "amount": str(payment.amount),
                        "invoice_id": str(payment.invoice_id),
                        "journal_reference": reference,
                    },
                )
        except IntegrityError:
            raise ValueError("Journal entry reference already exists.")
        return payment

    def _post_payable(self, payment):
        settings = PurchaseSettings.objects.for_tenant(self.tenant_id).first()
        if settings is None or not settings.accounts_payable_id:
            raise ValueError("Purchase accounting settings are not configured.")
        ap_account = settings.accounts_payable
        if (
            ap_account.tenant_id != self.tenant_id
            or not ap_account.is_active
            or ap_account.type != "Liability"
        ):
            raise ValueError("Purchase accounting settings are not configured.")
        try:
            with transaction.atomic():
                invoice = (
                    PurchaseInvoice.objects.for_tenant(self.tenant_id)
                    .select_for_update()
                    .get(pk=payment.purchase_invoice_id)
                )
                if invoice.status != PurchaseInvoice.Status.POSTED:
                    raise ValueError("Invoice is not posted.")
                amount = Decimal(str(payment.amount))
                if amount <= 0:
                    raise ValueError("Amount must be greater than zero.")
                if amount > self.purchase_outstanding(invoice):
                    raise ValueError("Amount exceeds the outstanding balance.")
                reference = (
                    f"PAY-PUR-{invoice.number}-{payment.number}"
                )
                entry = JournalEntry.objects.create(
                    tenant_id=self.tenant_id,
                    date=payment.payment_date,
                    description=(
                        f"Payment {payment.number} for purchase invoice "
                        f"{invoice.number}"
                    ),
                    reference=reference,
                    posted=True,
                    posted_at=timezone.now(),
                )
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=ap_account,
                    debit=amount,
                    credit=0,
                    description=(
                        f"Accounts payable for purchase invoice {invoice.number}"
                    ),
                )
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=payment.cash_account,
                    debit=0,
                    credit=amount,
                    description=(
                        f"Cash paid for purchase invoice {invoice.number}"
                    ),
                )
                payment.journal_entry = entry
                payment.status = Payment.Status.POSTED
                payment.posted_at = timezone.now()
                payment.save(update_fields=[
                    "journal_entry", "status", "posted_at", "updated_at",
                ])
                AuditService.record(
                    action="payment.post",
                    tenant_id=self.tenant_id,
                    target=payment,
                    before={"status": Payment.Status.DRAFT},
                    after={
                        "status": Payment.Status.POSTED,
                        "number": payment.number,
                        "amount": str(payment.amount),
                        "purchase_invoice_id": str(payment.purchase_invoice_id),
                        "journal_reference": reference,
                    },
                )
        except IntegrityError:
            raise ValueError("Journal entry reference already exists.")
        return payment