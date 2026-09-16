from rest_framework import serializers

from apps.accounting.serializers import TenantScopedAccountField
from apps.inventory.serializers import TenantScopedProductField
from apps.purchases import models
from apps.sales.models import Payment
from apps.sales.services import PaymentService


class TenantScopedVendorField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request")
        if request and hasattr(request, "tenant_id"):
            return models.Vendor.objects.for_tenant(request.tenant_id)
        return models.Vendor.objects.none()


class TenantScopedPostedPurchaseInvoiceField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request")
        if request and hasattr(request, "tenant_id"):
            return models.PurchaseInvoice.objects.for_tenant(
                request.tenant_id
            ).filter(status=models.PurchaseInvoice.Status.POSTED)
        return models.PurchaseInvoice.objects.none()


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Vendor
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
            raise serializers.ValidationError("Vendor name is required.")
        return value


class PurchaseSettingsSerializer(serializers.ModelSerializer):
    accounts_payable = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    expense_account = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    input_vat = TenantScopedAccountField(
        queryset=None,
        allow_null=True,
        required=False,
    )
    accounts_payable_name = serializers.CharField(
        source="accounts_payable.name", read_only=True, allow_null=True
    )
    expense_account_name = serializers.CharField(
        source="expense_account.name", read_only=True, allow_null=True
    )
    input_vat_name = serializers.CharField(
        source="input_vat.name", read_only=True, allow_null=True
    )

    class Meta:
        model = models.PurchaseSettings
        fields = [
            "id",
            "accounts_payable",
            "accounts_payable_name",
            "expense_account",
            "expense_account_name",
            "input_vat",
            "input_vat_name",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        for field in ("accounts_payable", "expense_account", "input_vat"):
            account = data.get(field)
            if account is None:
                continue
            expected_type = {
                "accounts_payable": "Liability",
                "expense_account": "Expense",
                "input_vat": "Asset",
            }[field]
            if account.type != expected_type:
                raise serializers.ValidationError(
                    {field: [f"Account must be of type {expected_type}."]}
                )
        return data


class PurchaseInvoiceLineSerializer(serializers.ModelSerializer):
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
        model = models.PurchaseInvoiceLine
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


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    vendor_id = TenantScopedVendorField(queryset=None)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    lines = PurchaseInvoiceLineSerializer(many=True)
    paid_amount = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()

    class Meta:
        model = models.PurchaseInvoice
        fields = [
            "id",
            "number",
            "vendor_id",
            "vendor_name",
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

    def get_paid_amount(self, obj):
        service = PaymentService(obj.tenant_id)
        return "{:.4f}".format(service.purchase_paid_amount(obj))

    def get_outstanding_balance(self, obj):
        service = PaymentService(obj.tenant_id)
        return "{:.4f}".format(service.purchase_outstanding(obj))

    def validate(self, data):
        if "number" in data:
            number = (data.get("number") or "").strip()
            if not number:
                raise serializers.ValidationError(
                    {"number": ["Invoice number is required."]}
                )
        invoice_date = data.get("invoice_date")
        due_date = data.get("due_date")
        if invoice_date and due_date and due_date < invoice_date:
            raise serializers.ValidationError(
                {"due_date": ["Due date cannot be before the invoice date."]}
            )
        return data

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        if "vendor_id" in validated_data:
            validated_data["vendor_id"] = getattr(
                validated_data["vendor_id"], "pk", validated_data["vendor_id"]
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance


class PurchaseInvoicePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PurchaseInvoice
        fields = ["id", "number", "status", "posted_at", "total"]


class PurchasePaymentSerializer(serializers.ModelSerializer):
    purchase_invoice_id = TenantScopedPostedPurchaseInvoiceField(queryset=None)
    purchase_invoice = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(
        source="purchase_invoice.vendor.name", read_only=True
    )
    cash_account = TenantScopedAccountField(queryset=None)
    cash_account_name = serializers.CharField(source="cash_account.name", read_only=True)
    journal_entry_id = serializers.UUIDField(
        source="journal_entry.id", read_only=True, allow_null=True
    )
    amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "number",
            "direction",
            "purchase_invoice_id",
            "purchase_invoice",
            "vendor_name",
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
            "direction",
            "purchase_invoice",
            "vendor_name",
            "cash_account_name",
            "status",
            "journal_entry_id",
            "posted_at",
            "created_at",
            "updated_at",
        ]

    def get_purchase_invoice(self, obj):
        invoice = obj.purchase_invoice
        service = PaymentService(obj.tenant_id)
        return {
            "id": str(invoice.id),
            "number": invoice.number,
            "vendor": {
                "id": str(invoice.vendor.id),
                "code": invoice.vendor.code,
                "name": invoice.vendor.name,
            },
            "total": "{:.4f}".format(invoice.total),
            "paid_amount": "{:.4f}".format(service.purchase_paid_amount(invoice)),
            "outstanding_balance": "{:.4f}".format(
                service.purchase_outstanding(invoice)
            ),
        }

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )
        return value

    def validate(self, data):
        invoice = data.get("purchase_invoice_id")
        amount = data.get("amount")
        if invoice is not None and amount is not None:
            request = self.context.get("request")
            outstanding = PaymentService(request.tenant_id).purchase_outstanding(
                invoice
            )
            if amount > outstanding:
                raise serializers.ValidationError(
                    {"amount": ["Amount exceeds the outstanding balance."]}
                )
        return data