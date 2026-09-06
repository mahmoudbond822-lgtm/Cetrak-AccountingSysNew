from decimal import Decimal

from django.db.models import Sum

from apps.accounting.models import Account, JournalEntry, JournalEntryLine


def _as_decimal(value):
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class AccountingService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def create_account(self, name, account_type, parent_id=None, description=None):
        parent_pk = parent_id.pk if hasattr(parent_id, 'pk') else parent_id
        account = Account.objects.create(
            tenant_id=self.tenant_id,
            name=name,
            type=account_type,
            parent_id=parent_pk,
            description=description,
        )
        return account

    def list_accounts(self, type=None, active_only=True):
        qs = Account.objects.for_tenant(self.tenant_id)
        if type:
            qs = qs.filter(type=type)
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    def list_accounts_tree(self, type=None):
        qs = self.list_accounts(type=type, active_only=True)
        root_accounts = qs.filter(parent__isnull=True)
        return root_accounts

    def get_account(self, account_id):
        return Account.objects.for_tenant(self.tenant_id).get(pk=account_id)

    def deactivate_account(self, account_id):
        account = self.get_account(account_id)
        if account.children.filter(is_active=True).exists():
            raise ValueError(
                "Cannot deactivate an account with active child accounts."
            )
        if account.journal_lines.exists():
            raise ValueError(
                "Cannot deactivate an account that has been used in journal entries."
            )
        account.is_active = False
        account.save()
        return account

    def account_is_used(self, account_id):
        account = self.get_account(account_id)
        return account.journal_lines.exists()

    def update_account(self, account_id, **kwargs):
        account = self.get_account(account_id)
        if "type" in kwargs and kwargs["type"] != account.type:
            if account.journal_lines.exists():
                raise ValueError(
                    "Cannot change the type of an account that has been used "
                    "in journal entries."
                )
        for key, value in kwargs.items():
            setattr(account, key, value)
        account.save()
        return account


class JournalEntryService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def create_entry(self, date, description, reference, lines_data):
        entry = JournalEntry.objects.create(
            tenant_id=self.tenant_id,
            date=date,
            description=description,
            reference=reference,
        )
        for line_data in lines_data:
            line_data = dict(line_data)
            line_data['account_id'] = getattr(line_data.get('account_id'), 'pk', line_data.get('account_id'))
            JournalEntryLine.objects.create(entry=entry, **line_data)
        return entry

    def list_entries(self, date_from=None, date_to=None):
        qs = JournalEntry.objects.for_tenant(self.tenant_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs.order_by("-date")

    def get_entry(self, entry_id):
        return JournalEntry.objects.for_tenant(self.tenant_id).get(pk=entry_id)

    def post_entry(self, entry_id):
        entry = self.get_entry(entry_id)
        if entry.posted:
            raise ValueError("Journal entry is already posted.")
        lines = entry.lines.all()
        total_debit = sum((line.debit for line in lines), Decimal("0"))
        total_credit = sum((line.credit for line in lines), Decimal("0"))
        if total_debit != total_credit:
            raise ValueError("Cannot post an imbalanced journal entry.")
        if not lines.exists():
            raise ValueError("Cannot post a journal entry with no lines.")
        entry.post_entry()
        return entry


class LedgerService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def get_ledger(self, account_id, date_from=None, date_to=None):
        account = Account.objects.for_tenant(self.tenant_id).get(pk=account_id)
        lines = JournalEntryLine.objects.filter(
            account_id=account_id,
            account__tenant_id=self.tenant_id,
            entry__tenant_id=self.tenant_id,
            entry__posted=True,
        ).select_related("entry").order_by("entry__date", "entry__created_at")

        if date_from:
            lines = lines.filter(entry__date__gte=date_from)
        if date_to:
            lines = lines.filter(entry__date__lte=date_to)

        entries = []
        running_balance = Decimal("0")
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for line in lines:
            running_balance += line.debit - line.credit
            total_debit += line.debit
            total_credit += line.credit
            entries.append({
                "date": line.entry.date,
                "description": line.entry.description,
                "reference": line.entry.reference,
                "debit": str(line.debit),
                "credit": str(line.credit),
                "running_balance": f"{running_balance:.4f}",
            })

        closing_balance = total_debit - total_credit

        return {
            "account": {
                "id": str(account.id),
                "name": account.name,
                "type": account.type,
            },
            "entries": entries,
            "totals": {
                "total_debit": f"{total_debit:.4f}",
                "total_credit": f"{total_credit:.4f}",
                "closing_balance": f"{closing_balance:.4f}",
            },
        }


class ReportService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def _line_aggregation(self, account_types, date_from=None, date_to=None):
        qs = JournalEntryLine.objects.filter(
            account__type__in=account_types,
            account__tenant_id=self.tenant_id,
            entry__tenant_id=self.tenant_id,
            entry__posted=True,
        )
        if date_from:
            qs = qs.filter(entry__date__gte=date_from)
        if date_to:
            qs = qs.filter(entry__date__lte=date_to)
        return qs.values(
            "account_id", "account__name", "account__type"
        ).annotate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        ).order_by("account__name")

    def trial_balance(self, date_from=None, date_to=None):
        rows = self._line_aggregation(
            ["Asset", "Liability", "Equity", "Revenue", "Expense"],
            date_from, date_to,
        )
        report_rows = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for row in rows:
            d = _as_decimal(row["total_debit"])
            c = _as_decimal(row["total_credit"])
            total_debit += d
            total_credit += c
            report_rows.append({
                "account_id": str(row["account_id"]),
                "account_name": row["account__name"],
                "account_type": row["account__type"],
                "debit": f"{d:.4f}",
                "credit": f"{c:.4f}",
            })
        return {
            "report_type": "trial-balance",
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "rows": report_rows,
            "totals": {
                "total_debit": f"{total_debit:.4f}",
                "total_credit": f"{total_credit:.4f}",
            },
        }

    def income_statement(self, date_from=None, date_to=None):
        rev_rows = self._line_aggregation(["Revenue"], date_from, date_to)
        exp_rows = self._line_aggregation(["Expense"], date_from, date_to)

        revenues = []
        total_revenue = Decimal("0")
        for row in rev_rows:
            bal = _as_decimal(row["total_credit"]) - _as_decimal(row["total_debit"])
            total_revenue += bal
            revenues.append({
                "account_id": str(row["account_id"]),
                "account_name": row["account__name"],
                "balance": f"{bal:.4f}",
            })

        expenses = []
        total_expenses = Decimal("0")
        for row in exp_rows:
            bal = _as_decimal(row["total_debit"]) - _as_decimal(row["total_credit"])
            total_expenses += bal
            expenses.append({
                "account_id": str(row["account_id"]),
                "account_name": row["account__name"],
                "balance": f"{bal:.4f}",
            })

        net_income = total_revenue - total_expenses

        return {
            "report_type": "income-statement",
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "revenues": revenues,
            "total_revenue": f"{total_revenue:.4f}",
            "expenses": expenses,
            "total_expenses": f"{total_expenses:.4f}",
            "net_income": f"{net_income:.4f}",
        }

    def balance_sheet(self, as_of=None):
        asset_rows = self._line_aggregation(
            ["Asset"], date_from=None, date_to=as_of
        )
        liability_rows = self._line_aggregation(
            ["Liability"], date_from=None, date_to=as_of
        )
        equity_rows = self._line_aggregation(
            ["Equity"], date_from=None, date_to=as_of
        )
        revenue_rows = self._line_aggregation(
            ["Revenue"], date_from=None, date_to=as_of
        )
        expense_rows = self._line_aggregation(
            ["Expense"], date_from=None, date_to=as_of
        )

        def build_section(rows, normal_balance):
            section = []
            total = Decimal("0")
            for row in rows:
                debit = _as_decimal(row["total_debit"])
                credit = _as_decimal(row["total_credit"])
                if normal_balance == "debit":
                    bal = debit - credit
                else:
                    bal = credit - debit
                total += bal
                section.append({
                    "account_id": str(row["account_id"]),
                    "account_name": row["account__name"],
                    "balance": f"{bal:.4f}",
                })
            return section, total

        assets, total_assets = build_section(asset_rows, "debit")
        liabilities, total_liabilities = build_section(liability_rows, "credit")
        equity, total_equity = build_section(equity_rows, "credit")

        total_revenue = sum(
            (
                _as_decimal(r["total_credit"]) - _as_decimal(r["total_debit"])
                for r in revenue_rows
            ),
            Decimal("0"),
        )
        total_expense = sum(
            (
                _as_decimal(r["total_debit"]) - _as_decimal(r["total_credit"])
                for r in expense_rows
            ),
            Decimal("0"),
        )
        net_income = total_revenue - total_expense
        if net_income != 0:
            equity.append({
                "account_id": "retained-earnings",
                "account_name": "Retained Earnings (Current Period)",
                "balance": f"{net_income:.4f}",
            })
            total_equity += net_income

        return {
            "report_type": "balance-sheet",
            "as_of": str(as_of) if as_of else None,
            "assets": assets,
            "total_assets": f"{total_assets:.4f}",
            "liabilities": liabilities,
            "total_liabilities": f"{total_liabilities:.4f}",
            "equity": equity,
            "total_equity": f"{total_equity:.4f}",
            "total_liabilities_and_equity": f"{total_liabilities + total_equity:.4f}",
        }