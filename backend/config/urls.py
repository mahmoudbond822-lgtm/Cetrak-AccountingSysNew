from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    from apps.core.health import check_redis
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False
    redis_ok = check_redis()
    return JsonResponse({
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "cache": "ok" if redis_ok else "unreachable",
    })

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/accounting/", include("apps.accounting.urls")),
    path("api/v1/sales/", include("apps.sales.urls")),
    path("api/v1/purchases/", include("apps.purchases.urls")),
    path("api/v1/inventory/", include("apps.inventory.urls")),
    path("api/v1/health/", health_check, name="health-check"),
]
