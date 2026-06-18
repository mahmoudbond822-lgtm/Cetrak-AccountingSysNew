from rest_framework.permissions import BasePermission


class HasAccountingAccess(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id is None:
            return False
        return request.user.memberships.filter(
            tenant_id=tenant_id,
            role__in=["Admin", "Accountant"],
        ).exists()
