"""Authentication throttling for the login and refresh endpoints (AUD-014).

The global DRF throttles in ``settings.REST_FRAMEWORK`` are deliberately blunt:
anon 20/hour and user 100/hour bound total API abuse, but they know nothing
about authentication, so they rate-limit successful logins and busy sessions
instead of repeated failed credential checks. These endpoint throttles are the
authentication-specific control, and each endpoint gets two independent layers:

* a per-client-address ceiling that bounds the total work an automated client
  can force the server to do (password hashing, token parsing, blacklisted
  token writes), and
* a second layer shaped like the actual attack — a failed-credential budget per
  account on login, and a refresh budget per token subject on refresh — which
  keeps working even when the client rotates its address.

Both layers keep their state in the Django cache (Redis in production), so the
limits hold across every web instance without a new table, and nothing derived
from a credential is ever stored.
"""

import logging

from django.conf import settings
from rest_framework.throttling import BaseThrottle, SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.services import LoginAttemptService, auth_throttle_settings

logger = logging.getLogger("cetrak.security.auth")


def throttle_enabled():
    """Master switch for the endpoint throttles (settings.AUTH_THROTTLE.ENABLED)."""
    return bool(auth_throttle_settings().get("ENABLED", True))


def client_ident(request):
    """Client address used for throttling.

    ``X-Forwarded-For`` is supplied by the client and can be forged unless a
    trusted proxy overwrites it, so it is honoured only where the deployment
    says it is trustworthy. The left-most entry is the originating client.
    """
    if auth_throttle_settings().get("TRUST_X_FORWARDED_FOR"):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def _submitted_email(request):
    """Normalised email address from a login request body, if there is one."""
    try:
        data = request.data
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    email = data.get("email")
    return str(email).strip().lower() if email else None


def _verified_refresh_subject(request):
    """Identifier for a refresh call, without trusting an unverified token.

    Rotation mints a new ``jti`` on every call, so a per-token budget would
    reset itself for free and a stolen token could be rotated indefinitely. The
    budget is therefore keyed on the ``user_id`` claim — but only once the
    signature has been verified, so a forged token can never spend another
    account's budget. Anything unparseable falls back to the client address.
    """
    raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if not raw:
        return None
    try:
        token = RefreshToken(raw)
    except Exception:
        return None
    user_id = token.get("user_id")
    return f"user:{user_id}" if user_id else None


class _AddressThrottle(SimpleRateThrottle):
    """Request-rate ceiling per client address.

    Subclasses declare ``scope`` plus the settings key holding their rate. The
    rate is resolved per request rather than captured in a class attribute, so
    the limits stay in settings and can be overridden in tests.
    """

    rate_setting = None

    def get_rate(self):
        if not throttle_enabled():
            return None
        return auth_throttle_settings().get(self.rate_setting) or None

    def get_cache_key(self, request, view):
        if not throttle_enabled():
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": client_ident(request),
        }


class LoginAddressThrottle(_AddressThrottle):
    """Per-address ceiling on login attempts, successes included.

    This is a resource brake, not the brute-force brake: its job is to keep a
    single automated client from forcing unbounded bcrypt work, so it counts
    every request that reaches the endpoint.
    """

    scope = "login_address"
    rate_setting = "LOGIN_IP_RATE"


class LoginAccountThrottle(BaseThrottle):
    """Refuses password checking for an account that spent its failure budget.

    The counting rules live in :class:`LoginAttemptService`; this class only
    turns its verdict into DRF's generic 429. Because the check runs before the
    view, a refused attempt costs one cache read instead of a bcrypt hash.

    The response is the same generic 429 — same body, same status — for a real
    account, an address that does not exist and an address nobody has ever used,
    because unknown addresses consume the same budget. It therefore discloses
    nothing about which accounts exist.
    """

    def __init__(self):
        # ``APIView.check_throttles`` asks every throttle it consults for a
        # ``duration``/``wait()``, so both must always exist.
        self.duration = None
        self.ident = None

    def wait(self):
        """Seconds the client should wait before retrying, for ``Retry-After``.

        Returning ``None`` (the ``BaseThrottle`` default) throttles the request
        but leaves the client with no idea when to come back, so the remaining
        window is reported instead.
        """
        return self.duration

    def allow_request(self, request, view):
        if not throttle_enabled():
            return True
        email = _submitted_email(request)
        if not email:
            return True  # malformed body: the serializer answers 400
        service = LoginAttemptService()
        blocked_for = service.blocked_seconds(email)
        if blocked_for <= 0:
            return True
        self.duration = blocked_for
        self.ident = service.account_ident(email)[:12]
        logger.debug(
            "Login throttled: account=%s client=%s path=%s retry_after=%ss",
            self.ident,
            client_ident(request),
            request.path,
            blocked_for,
        )
        return False


class RefreshAddressThrottle(_AddressThrottle):
    """Per-address ceiling on refresh calls, bounding token-parse and DB work."""

    scope = "refresh_address"
    rate_setting = "REFRESH_IP_RATE"


class RefreshSubjectThrottle(_AddressThrottle):
    """Per-token-subject ceiling on refresh calls.

    Keyed on the verified ``user_id`` claim so it survives rotation, which
    bounds how often one session can be rotated (and therefore how many
    blacklisted-token rows and cache operations it can generate).
    """

    scope = "refresh_subject"
    rate_setting = "REFRESH_SESSION_RATE"

    def get_cache_key(self, request, view):
        if not throttle_enabled():
            return None
        ident = _verified_refresh_subject(request) or client_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
