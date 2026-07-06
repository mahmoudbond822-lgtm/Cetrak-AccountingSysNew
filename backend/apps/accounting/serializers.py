from rest_framework import serializers

from apps.accounting import models


class AccountSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_id = serializers.UUIDField(allow_null=True, required=False)

    class Meta:
        model = models.Account
        fields = [
            "id",
            "name",
            "type",
            "parent_id",
            "description",
            "is_active",
            "children",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "children"]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return AccountSerializer(children, many=True).data

    def validate_parent_id(self, value):
        if value is None:
            return value
        if not isinstance(value, models.Account):
            try:
                value = models.Account.objects.for_tenant(
                    self.context["request"].tenant_id
                ).get(pk=value)
            except models.Account.DoesNotExist:
                raise serializers.ValidationError(
                    "Parent account does not exist."
                )
        depth = 0
        current = value
        seen = set()
        while current is not None:
            if current.pk in seen:
                raise serializers.ValidationError("Circular reference detected.")
            seen.add(current.pk)
            depth += 1
            if depth > 10:
                raise serializers.ValidationError(
                    "Account hierarchy depth exceeds maximum of 10 levels."
                )
            current = current.parent
        return value


class TenantScopedAccountField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get("request")
        if request and hasattr(request, "tenant_id"):
            return models.Account.objects.for_tenant(request.tenant_id)
        return models.Account.objects.none()


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_type = serializers.CharField(source="account.type", read_only=True)
    account_id = TenantScopedAccountField(
        queryset=models.Account.objects.none(),
    )

    class Meta:
        model = models.JournalEntryLine
        fields = [
            "id",
            "account_id",
            "account_name",
            "account_type",
            "debit",
            "credit",
            "description",
        ]
        read_only_fields = ["id", "account_name", "account_type"]

    def validate(self, data):
        debit = data.get("debit", 0)
        credit = data.get("credit", 0)
        if debit and credit:
            raise serializers.ValidationError(
                "A line cannot have both debit and credit amounts."
            )
        if not debit and not credit:
            raise serializers.ValidationError(
                "A line must have either a debit or a credit amount."
            )
        if debit < 0 or credit < 0:
            raise serializers.ValidationError("Amounts must be non-negative.")
        return data


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True)
    total_debit = serializers.DecimalField(
        max_digits=19, decimal_places=4, read_only=True
    )
    total_credit = serializers.DecimalField(
        max_digits=19, decimal_places=4, read_only=True
    )
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = models.JournalEntry
        fields = [
            "id",
            "date",
            "description",
            "reference",
            "line_count",
            "total_debit",
            "total_credit",
            "lines",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "line_count", "total_debit", "total_credit"]

    def get_line_count(self, obj):
        return obj.lines.count()

    def validate(self, data):
        lines = data.get("lines", [])
        if len(lines) < 2:
            raise serializers.ValidationError(
                "A journal entry must have at least 2 lines."
            )
        total_debit = sum(float(line.get("debit", 0)) for line in lines)
        total_credit = sum(float(line.get("credit", 0)) for line in lines)
        if abs(total_debit - total_credit) > 0.001:
            raise serializers.ValidationError(
                f"Journal entry is not balanced. Total debits ({total_debit:.4f}) "
                f"do not equal total credits ({total_credit:.4f})."
            )
        if total_debit == 0 and total_credit == 0:
            raise serializers.ValidationError(
                "A journal entry cannot have all zero amounts."
            )
        return data

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        entry = models.JournalEntry.objects.create(**validated_data)
        for line_data in lines_data:
            line_data = dict(line_data)
            line_data['account_id'] = getattr(line_data.get('account_id'), 'pk', line_data.get('account_id'))
            models.JournalEntryLine.objects.create(
                entry=entry, **line_data
            )
        return entry


class JournalEntryPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JournalEntry
        fields = ["id", "posted", "posted_at", "reference", "date"]


class LedgerEntrySerializer(serializers.Serializer):
    date = serializers.DateField()
    description = serializers.CharField()
    reference = serializers.CharField()
    debit = serializers.CharField()
    credit = serializers.CharField()
    running_balance = serializers.CharField()


class LedgerAccountSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()


class LedgerTotalsSerializer(serializers.Serializer):
    total_debit = serializers.CharField()
    total_credit = serializers.CharField()
    closing_balance = serializers.CharField()


class LedgerSerializer(serializers.Serializer):
    account = LedgerAccountSerializer()
    entries = LedgerEntrySerializer(many=True)
    totals = LedgerTotalsSerializer()


class ReportRowSerializer(serializers.Serializer):
    account_id = serializers.CharField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    debit = serializers.CharField()
    credit = serializers.CharField()


class ReportTotalsSerializer(serializers.Serializer):
    total_debit = serializers.CharField()
    total_credit = serializers.CharField()


class TrialBalanceSerializer(serializers.Serializer):
    report_type = serializers.CharField()
    date_from = serializers.CharField(allow_null=True)
    date_to = serializers.CharField(allow_null=True)
    rows = ReportRowSerializer(many=True)
    totals = ReportTotalsSerializer()


class AccountBalanceSerializer(serializers.Serializer):
    account_id = serializers.CharField()
    account_name = serializers.CharField()
    balance = serializers.CharField()


class IncomeStatementSerializer(serializers.Serializer):
    report_type = serializers.CharField()
    date_from = serializers.CharField(allow_null=True)
    date_to = serializers.CharField(allow_null=True)
    revenues = AccountBalanceSerializer(many=True)
    total_revenue = serializers.CharField()
    expenses = AccountBalanceSerializer(many=True)
    total_expenses = serializers.CharField()
    net_income = serializers.CharField()


class BalanceSheetSectionSerializer(serializers.Serializer):
    account_id = serializers.CharField()
    account_name = serializers.CharField()
    balance = serializers.CharField()


class BalanceSheetSerializer(serializers.Serializer):
    report_type = serializers.CharField()
    as_of = serializers.CharField(allow_null=True)
    assets = BalanceSheetSectionSerializer(many=True)
    total_assets = serializers.CharField()
    liabilities = BalanceSheetSectionSerializer(many=True)
    total_liabilities = serializers.CharField()
    equity = BalanceSheetSectionSerializer(many=True)
    total_equity = serializers.CharField()
    total_liabilities_and_equity = serializers.CharField()
