from apps.core.permissions import TenantScopedPermission


class CanViewPurchases(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant", "Manager"]


class CanManagePurchases(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant"]


class CanPostPurchaseInvoice(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant"]


class CanConfigurePurchases(TenantScopedPermission):
    allowed_roles = ["Admin"]