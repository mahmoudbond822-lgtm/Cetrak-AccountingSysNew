import os
from django.core.cache import cache

def check_redis():
    try:
        cache.set("_health_check", "ok", timeout=5)
        return cache.get("_health_check") == "ok"
    except Exception:
        return False
