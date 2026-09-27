from decimal import Decimal

from rest_framework import serializers

from apps.accounting.serializers import TenantScopedAccountField
from apps.inventory.serializers import TenantScopedProductField
from apps.sales import models
from apps.sales.services import PaymentService


class TenantScopedCustomerField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request")
        if request and hasattr(request, "tenant_id"):
            return models.Customer.objects.for_tenant(request.tenant_id)
        return models.Customer.objects.none()


class TenantScopedPostedInvoiceField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request")
        if request and hasattr(request, "tenant_id"):
            return models.SalesInvoice.objects.for_tenant(request.tenant_id).filter(
                status=models.SalesInvoice.Status.POSTED
            )
        return models.SalesInvoice.objects.none()


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Customer
        fields = [
            "id",
            "code",
            "name",
            "email",
            "phone",
            "address",
            "tax_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "code": {"required": False, "allow_blank": True},
        }

    def validate_code(self, value):
        value = (value or "").strip()
        return value or None

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Customer name is required.")
        return value


class SalesSettingsSerializer(serializers.ModelSerializer):
    accounts_receivable = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    sales_revenue = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    vat_payable = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    accounts_receivable_name = serializers.CharField(
        source="accounts_receivable.name", read_only=True, allow_null=True
    )
    sales_revenue_name = serializers.CharField(
        source="sales_revenue.name", read_only=True, allow_null=True
    )
    vat_payable_name = serializers.CharField(
        source="vat_payable.name", read_only=True, allow_null=True
    )

    class Meta:
        model = models.SalesSettings
        fields = [
            "id",
            "accounts_receivable",
            "accounts_receivable_name",
            "sales_revenue",
            "sales_revenue_name",
            "vat_payable",
            "vat_payable_name",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        for field in ("accounts_receivable", "sales_revenue", "vat_payable"):
            account = data.get(field)
            if account is None:
                continue
            expected_type = {
                "accounts_receivable": "Asset",
                "sales_revenue": "Revenue",
                "vat_payable": "Liability",
            }[field]
            if account.type != expected_type:
                raise serializers.ValidationError(
                    {field: [f"Account must be of type {expected_type}."]}
                )
        return data


class SalesInvoiceLineSerializer(serializers.ModelSerializer):
    product_id = TenantScopedProductField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    product_sku = serializers.CharField(
        source="product.sku", read_only=True, allow_null=True
    )
    product_name = serializers.CharField(
        source="product.name", read_only=True, allow_null=True
    )

    class Meta:
        model = models.SalesInvoiceLine
        fields = [
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "subtotal",
            "tax",
            "total",
        ]
        read_only_fields = ["id", "subtotal", "tax", "total"]

    def validate_description(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Line description is required.")
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Unit price must not be negative."
            )
        return value

    def validate_tax_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Tax rate must be between 0 and 100."
            )
        return value


class SalesInvoiceSerializer(serializers.ModelSerializer):
    customer_id = TenantScopedCustomerField(queryset=None)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    lines = SalesInvoiceLineSerializer(many=True)
    paid_amount = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()

    class Meta:
        model = models.SalesInvoice
        fields = [
            "id",
            "number",
            "customer_id",
            "customer_name",
            "invoice_date",
            "due_date",
            "status",
            "discount",
            "subtotal",
            "tax",
            "total",
            "notes",
            "paid_amount",
            "outstanding_balance",
            "posted_at",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "subtotal",
            "tax",
            "total",
            "paid_amount",
            "outstanding_balance",
            "posted_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "number": {"required": False, "allow_blank": True},
        }

    def get_paid_amount(self, obj):
        paid = getattr(obj, "paid_amount", None)
        if paid is None:
            paid = PaymentService(obj.tenant_id).invoice_paid_amount(obj)
        return "{:.4f}".format(paid)

    def get_outstanding_balance(self, obj):
        paid = getattr(obj, "paid_amount", None)
        if paid is None:
            paid = PaymentService(obj.tenant_id).invoice_paid_amount(obj)
        outstanding = max(obj.total - paid, Decimal("0"))
        return "{:.4f}".format(outstanding)

    def validate(self, data):
        invoice_date = data.get("invoice_date")
        due_date = data.get("due_date")
        if invoice_date and due_date and due_date < invoice_date:
            raise serializers.ValidationError(
                {"due_date": ["Due date cannot be before the invoice date."]}
            )
        return data

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        if "customer_id" in validated_data:
            validated_data["customer_id"] = getattr(
                validated_data["customer_id"], "pk", validated_data["customer_id"]
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance


class SalesInvoicePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SalesInvoice
        fields = ["id", "number", "status", "posted_at", "total"]


class PaymentSerializer(serializers.ModelSerializer):
    invoice_id = TenantScopedPostedInvoiceField(queryset=None)
    invoice = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="invoice.customer.name", read_only=True)
    cash_account = TenantScopedAccountField(queryset=None)
    cash_account_name = serializers.CharField(source="cash_account.name", read_only=True)
    journal_entry_id = serializers.UUIDField(
        source="journal_entry.id", read_only=True, allow_null=True
    )

    class Meta:
        model = models.Payment
        fields = [
            "id",
            "number",
            "invoice_id",
            "invoice",
            "customer_name",
            "payment_date",
            "amount",
            "method",
            "cash_account",
            "cash_account_name",
            "reference",
            "notes",
            "status",
            "journal_entry_id",
            "posted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "invoice",
            "customer_name",
            "cash_account_name",
            "status",
            "journal_entry_id",
            "posted_at",
            "created_at",
            "updated_at",
        ]

    def get_invoice(self, obj):
        invoice = obj.invoice
        paid = getattr(obj, "_invoice_paid", None)
        if paid is None:
            paid = PaymentService(obj.tenant_id).invoice_paid_amount(invoice)
        return {
            "id": str(invoice.id),
            "number": invoice.number,
            "customer": {
                "id": str(invoice.customer.id),
                "code": invoice.customer.code,
                "name": invoice.customer.name,
            },
            "total": "{:.4f}".format(invoice.total),
            "paid_amount": "{:.4f}".format(paid),
            "outstanding_balance": "{:.4f}".format(
                max(invoice.total - paid, Decimal("0"))
            ),
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, data):
        invoice = data.get("invoice_id")
        amount = data.get("amount")
        if invoice is not None and amount is not None:
            request = self.context.get("request")
            outstanding = PaymentService(request.tenant_id).invoice_outstanding(invoice)
            if amount > outstanding:
                raise serializers.ValidationError(
                    {"amount": ["Amount exceeds the outstanding balance."]}
                )
        return data
