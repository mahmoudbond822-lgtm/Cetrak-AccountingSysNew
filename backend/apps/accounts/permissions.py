from rest_framework.permissions import BasePermission

from apps.accounts.models import Membership


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            return False
        return Membership.objects.filter(
            user=request.user,
            tenant_id=tenant_id,
            role=Membership.Role.ADMIN,
        ).exists()
