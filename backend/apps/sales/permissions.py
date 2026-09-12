from apps.core.permissions import TenantScopedPermission


class CanViewSales(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant", "Manager"]


class CanManageSales(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant"]


class CanPostSalesInvoice(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant"]


class CanConfigureSales(TenantScopedPermission):
    allowed_roles = ["Admin"]