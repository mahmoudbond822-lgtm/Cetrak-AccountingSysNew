from apps.core.permissions import TenantScopedPermission


class HasAccountingAccess(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant"]


class CanViewReports(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant", "Manager"]