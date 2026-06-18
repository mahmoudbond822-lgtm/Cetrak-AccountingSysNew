from django.db import connection

from apps.accounting.models import Account


class AccountingService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def create_account(self, name, type, parent_id=None, description=None):
        account = Account.objects.create(
            tenant_id=self.tenant_id,
            name=name,
            type=type,
            parent_id=parent_id,
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
        from apps.accounting.models import JournalEntry, JournalEntryLine

        entry = JournalEntry.objects.create(
            tenant_id=self.tenant_id,
            date=date,
            description=description,
            reference=reference,
        )
        for line_data in lines_data:
            JournalEntryLine.objects.create(entry=entry, **line_data)
        return entry

    def list_entries(self, date_from=None, date_to=None):
        from apps.accounting.models import JournalEntry

        qs = JournalEntry.objects.for_tenant(self.tenant_id)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs.order_by("-date")

    def get_entry(self, entry_id):
        from apps.accounting.models import JournalEntry

        return JournalEntry.objects.for_tenant(self.tenant_id).get(pk=entry_id)
