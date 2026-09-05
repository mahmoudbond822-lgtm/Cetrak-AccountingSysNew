from rest_framework.permissions import BasePermission


class CanViewSales(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin", "Accountant", "Manager"],
        ).exists()


class CanManageSales(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin", "Accountant"],
        ).exists()


class CanPostSalesInvoice(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin", "Accountant"],
        ).exists()


class CanConfigureSales(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.memberships.filter(
            tenant_id=request.tenant_id,
            role__in=["Admin"],
        ).exists()