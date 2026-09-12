from apps.core.permissions import TenantScopedPermission


class CanViewInventory(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant", "Manager"]


class CanManageInventory(TenantScopedPermission):
    allowed_roles = ["Admin", "Accountant"]


class CanConfigureInventory(TenantScopedPermission):
    allowed_roles = ["Admin"]