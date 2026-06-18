from rest_framework import serializers

from apps.accounting import models


class AccountSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

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


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_type = serializers.CharField(source="account.type", read_only=True)

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
        total_debit = sum(line["debit"] for line in lines)
        total_credit = sum(line["credit"] for line in lines)
        if total_debit != total_credit:
            raise serializers.ValidationError(
                f"Journal entry is not balanced. Total debits ({total_debit}) "
                f"do not equal total credits ({total_credit})."
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
            models.JournalEntryLine.objects.create(
                entry=entry, **line_data
            )
        return entry
