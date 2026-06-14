from django.utils.deprecation import MiddlewareMixin


class TenantResolutionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tenant_id = request.META.get("HTTP_X_TENANT_ID")
        request.tenant_id = tenant_id
