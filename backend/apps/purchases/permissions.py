from rest_framework.permissions import BasePermission


class CanViewPurchases(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin", "Accountant", "Manager"],
        ).exists()


class CanManagePurchases(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin", "Accountant"],
        ).exists()


class CanPostPurchaseInvoice(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin", "Accountant"],
        ).exists()


class CanConfigurePurchases(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin"],
        ).exists()