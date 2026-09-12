import base64
import json
import uuid

from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from apps.accounts.models import Membership
from apps.core.audit import clear_request_context

ALLOWED_PATHS = {
    "/api/v1/auth/register/",
    "/api/v1/auth/login/",
    "/api/v1/auth/refresh/",
    "/api/v1/auth/logout/",
}


def _parse_jwt_payload(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    parts = auth_header.split(".") if "." in auth_header else None
    if not parts or len(parts) != 3:
        return None
    try:
        payload = parts[1]
        padded = payload + "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded)
    except Exception:
        return None


class TenantResolutionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        clear_request_context()
        tenant_id = None

        payload = _parse_jwt_payload(request.META.get("HTTP_AUTHORIZATION"))
        if payload:
            tenant_id = payload.get("tenant_id")

        if not tenant_id:
            tenant_id = request.META.get("HTTP_X_TENANT_ID")

        path = request.META.get("PATH_INFO", "")
        if path.startswith("/api/v1/tenants/switch/"):
            request.tenant_id = None
            return

        if not tenant_id:
            if path in ALLOWED_PATHS:
                request.tenant_id = None
                return
            if request.user and request.user.is_authenticated:
                return HttpResponseForbidden(
                    '{"detail": "No tenant context provided."}',
                    content_type="application/json",
                )
            request.tenant_id = None
            return

        try:
            request.tenant_id = uuid.UUID(tenant_id)
        except ValueError:
            return HttpResponseForbidden(
                '{"detail": "Invalid tenant ID format."}',
                content_type="application/json",
            )

        if request.user and request.user.is_authenticated:
            if not Membership.objects.for_tenant(request.tenant_id).filter(
                user=request.user
            ).exists():
                return HttpResponseForbidden(
                    '{"detail": "You do not have access to this tenant."}',
                    content_type="application/json",
                )

    def process_response(self, request, response):
        clear_request_context()
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        from django.conf import settings

        csp = getattr(settings, "CONTENT_SECURITY_POLICY", None)
        if csp and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = csp
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response
