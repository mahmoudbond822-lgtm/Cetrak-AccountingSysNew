from rest_framework.permissions import BasePermission

from apps.accounts.models import User
from apps.core.models import Tenant


class TenantScopedPermission(BasePermission):
    """Base permission enforcing active-user, active-tenant, and membership.

    Subclasses declare the membership roles that are allowed to access the
    view via ``allowed_roles``. A single query verifies the membership exists
    with an allowed role *and* that the tenant is ACTIVE; the user status is
    cheaply checked on the already-loaded ``request.user``. This closes the
    "disabled user / suspended or cancelled tenant keeps API access" gap
    (AUD-007) for every tenant-scoped endpoint.
    """

    allowed_roles = []

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "status", None) != User.Status.ACTIVE:
            return False
        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id is None:
            return False
        return user.memberships.filter(
            tenant_id=tenant_id,
            role__in=self.allowed_roles,
            tenant__status=Tenant.Status.ACTIVE,
        ).exists()