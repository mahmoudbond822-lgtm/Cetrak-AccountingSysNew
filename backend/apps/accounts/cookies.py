import secrets

from datetime import timedelta

from django.conf import settings


def refresh_cookie_kwargs(remember_me=False, secure=None):
    jwt_settings = settings.SIMPLE_JWT
    if secure is None:
        secure = settings.REFRESH_COOKIE_SECURE
    lifetime = (
        jwt_settings.get("REFRESH_TOKEN_LIFETIME_REMEMBER_ME", timedelta(days=30))
        if remember_me
        else jwt_settings.get("REFRESH_TOKEN_LIFETIME", timedelta(days=7))
    )
    return {
        "key": settings.REFRESH_COOKIE_NAME,
        "max_age": int(lifetime.total_seconds()),
        "path": settings.REFRESH_COOKIE_PATH,
        "secure": secure,
        "httponly": True,
        "samesite": settings.REFRESH_COOKIE_SAMESITE,
    }


def set_refresh_cookie(response, refresh_token, remember_me=False):
    kwargs = refresh_cookie_kwargs(remember_me=remember_me)
    response.set_cookie(
        kwargs["key"],
        str(refresh_token),
        max_age=kwargs["max_age"],
        path=kwargs["path"],
        secure=kwargs["secure"],
        httponly=kwargs["httponly"],
        samesite=kwargs["samesite"],
    )


def delete_refresh_cookie(response):
    kwargs = refresh_cookie_kwargs()
    response.delete_cookie(
        kwargs["key"],
        path=kwargs["path"],
        samesite=kwargs["samesite"],
    )


def set_csrf_cookie(response, token):
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        token,
        max_age=getattr(settings, "CSRF_COOKIE_AGE", None),
        path=getattr(settings, "CSRF_COOKIE_PATH", "/") or "/",
        secure=getattr(settings, "CSRF_COOKIE_SECURE", False),
        httponly=getattr(settings, "CSRF_COOKIE_HTTPONLY", False),
        samesite=getattr(settings, "CSRF_COOKIE_SAMESITE", "Lax"),
    )


def csrf_invalid(request):
    cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
    header = request.META.get("HTTP_X_CSRFTOKEN")
    if not cookie or not header:
        return True
    return not secrets.compare_digest(header, cookie)