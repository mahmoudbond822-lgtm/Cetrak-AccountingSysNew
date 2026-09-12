from apps.core.permissions import TenantScopedPermission


class IsAdminUser(TenantScopedPermission):
    allowed_roles = ["Admin"]