from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory

from apps.core.middleware import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    def test_csp_and_security_headers_set_on_all_responses(self):
        request = RequestFactory().get("/api/v1/health/")
        response = HttpResponse()

        middleware = SecurityHeadersMiddleware(lambda req: response)
        middleware(request)

        assert response["Content-Security-Policy"] == settings.CONTENT_SECURITY_POLICY
        assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
        assert "object-src 'none'" in response["Content-Security-Policy"]
        assert "'unsafe-inline'" not in response["Content-Security-Policy"]
        assert response["X-Content-Type-Options"] == "nosniff"
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response

    def test_existing_csp_header_is_not_overwritten(self):
        request = RequestFactory().get("/")
        response = HttpResponse()
        response["Content-Security-Policy"] = "default-src 'none'"

        middleware = SecurityHeadersMiddleware(lambda req: response)
        middleware(request)

        assert response["Content-Security-Policy"] == "default-src 'none'"