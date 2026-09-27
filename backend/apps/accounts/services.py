import datetime as dt_mod
import logging
import math
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Tenant
from apps.core.audit import AuditService
from apps.accounts.models import User, Membership, BlacklistedToken, Invitation

logger = logging.getLogger("cetrak.security.auth")

_cache_failure_reported = False


def _email_key(email):
    return str(email or "").strip().lower()


def auth_throttle_settings():
    """Named authentication throttle configuration (see settings.AUTH_THROTTLE)."""
    return getattr(settings, "AUTH_THROTTLE", {}) or {}


class LoginAttemptService:
    """Failed-credential accounting for the login endpoint (AUD-014).

    Design notes
    ------------
    * Existence agnostic: a failure is recorded for an unknown address exactly
      as for a wrong password, so a throttled response cannot be used to
      discover which addresses exist.
    * Bounded in time: the window TTL is written once, by the first failure, and
      later failures only increment the counter. A sustained attack therefore
      cannot hold an account blocked beyond ``LOGIN_ACCOUNT_WINDOW_SECONDS``,
      which is what keeps a targeted lock-out from becoming a denial of
      service.
    * Self-healing: a successful login deletes the state, so the account works
      again the moment its owner proves possession of the password.
    * Opaque keys: an account is identified by a keyed HMAC of the normalised
      address, so neither the address nor any credential is written to the
      cache or to the logs.

    State lives in the Django cache (Redis in production) and is deliberately
    not persisted: a table of login attempts would add a database write to
    every failed login, the exact amplification this control exists to stop.
    """

    KEY_PREFIX = "throttle:auth:login:account"

    def __init__(self, cache_backend=None):
        self._cache = cache_backend if cache_backend is not None else cache

    # -- keys -------------------------------------------------------------
    def account_ident(self, email):
        """Stable, opaque identifier for a login address."""
        return salted_hmac("apps.accounts.login", _email_key(email)).hexdigest()

    def _count_key(self, ident):
        return f"{self.KEY_PREFIX}:{ident}:count"

    def _until_key(self, ident):
        return f"{self.KEY_PREFIX}:{ident}:until"

    # -- cache access -----------------------------------------------------
    def _report_cache_failure(self):
        global _cache_failure_reported
        if _cache_failure_reported:
            logger.debug(
                "Authentication throttle cache operation failed.", exc_info=True
            )
            return
        _cache_failure_reported = True
        logger.warning(
            "Authentication throttling is degraded: the cache is unavailable, "
            "so login throttling is not enforced for this request.",
            exc_info=True,
        )

    def _call(self, operation, *args):
        """Run a cache operation, degrading to *fail open* if the cache is down.

        The cache is shared infrastructure: if it is unreachable, refusing
        requests would turn an infrastructure outage into a lock-out of every
        user, so the control is skipped instead — but never silently, see
        :meth:`_report_cache_failure`.
        """
        try:
            return operation(*args)
        except Exception:
            self._report_cache_failure()
            return None

    def _incr(self, key):
        """Atomic increment that leaves the window TTL untouched."""
        try:
            return self._cache.incr(key)
        except ValueError:
            return None  # key expired between create() and increment()
        except Exception:
            self._report_cache_failure()
            return None

    # -- accounting -------------------------------------------------------
    def record_failure(self, email):
        """Count one failed credential check and return the new count."""
        window = self.window_seconds()
        ident = self.account_ident(email)
        count_key = self._count_key(ident)

        if self._call(self._cache.add, count_key, 1, window):
            # First failure of the window: it starts the count and publishes a
            # fixed expiry, so the remaining block time can be reported later
            # without re-arming the TTL on every subsequent failure.
            self._call(
                self._cache.add, self._until_key(ident), time.time() + window, window
            )
            return 1

        # Only increment: the window must stay the one the first failure
        # started, otherwise a sustained attack could hold an account blocked
        # for as long as it kept hammering.
        count = self._incr(count_key)
        if count is None:
            self._call(self._cache.set, count_key, 1, window)
            return 1
        if count == self.failure_limit():
            # One line per account per window: enough to see an attack without
            # turning every refused attempt into log volume. No address, no
            # credential, just the keyed identifier.
            logger.warning(
                "Login failure budget exhausted: account=%s failures=%d window=%ss",
                ident[:12],
                count,
                window,
            )
        return count

    def record_success(self, email):
        """Clear the failure state: a successful login always starts clean."""
        ident = self.account_ident(email)
        self._call(self._cache.delete, self._count_key(ident))
        self._call(self._cache.delete, self._until_key(ident))

    def blocked_seconds(self, email):
        """Seconds during which credential checking stays refused (0 = allowed).

        Rounded up: the value is published to clients as ``Retry-After``, and a
        client that waits exactly as long as it was told must find the block over.
        """
        ident = self.account_ident(email)
        count = self._call(self._cache.get, self._count_key(ident))
        if not isinstance(count, int) or count < self.failure_limit():
            return 0
        until = self._call(self._cache.get, self._until_key(ident))
        if not isinstance(until, (int, float)):
            return self.window_seconds()  # conservative fallback
        return max(0, math.ceil(until - time.time()))

    def is_blocked(self, email):
        return self.blocked_seconds(email) > 0

    def failure_limit(self):
        return int(auth_throttle_settings().get("LOGIN_ACCOUNT_FAILURE_LIMIT", 5))

    def window_seconds(self):
        return int(
            auth_throttle_settings().get("LOGIN_ACCOUNT_WINDOW_SECONDS", 15 * 60)
        )


class AuthService:
    @transaction.atomic
    def register(self, email, password, company_name):
        try:
            user = User.objects.create_user(email=email, password=password)
        except IntegrityError:
            raise ValueError("A user with this email already exists.")
        tenant = Tenant.objects.create(name=company_name)
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role=Membership.Role.ADMIN,
        )
        refresh = RefreshToken()
        refresh["user_id"] = str(user.id)
        refresh["tenant_id"] = str(tenant.id)
        AuditService.record(
            action="auth.register",
            tenant_id=tenant.id,
            target=user,
            actor=user,
            after={
                "email": user.email,
                "display_name": user.display_name,
                "status": user.status,
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name,
                "role": Membership.Role.ADMIN,
            },
        )
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "status": user.status,
            },
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "status": tenant.status,
            },
        }

    def login(self, email, password, remember_me=False):
        from django.conf import settings

        attempts = LoginAttemptService()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Counted exactly like a wrong password: the throttle must not
            # become an oracle for which addresses exist (AUD-014).
            attempts.record_failure(email)
            return None, "Invalid email or password."

        if user.status == User.Status.DISABLED:
            return None, "Account has been disabled. Contact your administrator."

        if not user.check_password(password):
            attempts.record_failure(email)
            return None, "Invalid email or password."

        memberships = list(
            Membership.objects.filter(
                user=user, tenant__status=Tenant.Status.ACTIVE
            ).select_related("tenant")
        )

        if not memberships:
            return None, "Account has no active tenant memberships."

        tenants_data = [
            {
                "id": str(m.tenant.id),
                "name": m.tenant.name,
                "role": m.role,
            }
            for m in memberships
        ]

        jwt_settings = settings.SIMPLE_JWT
        refresh_lifetime = jwt_settings.get("REFRESH_TOKEN_LIFETIME_REMEMBER_ME", dt_mod.timedelta(days=30)) if remember_me else jwt_settings.get("REFRESH_TOKEN_LIFETIME", dt_mod.timedelta(days=7))
        refresh = RefreshToken()
        refresh.set_exp(lifetime=refresh_lifetime)
        refresh["user_id"] = str(user.id)

        active_tenant = None
        if len(memberships) == 1:
            m = memberships[0]
            active_tenant = {"id": str(m.tenant.id), "name": m.tenant.name, "role": m.role}
            refresh["tenant_id"] = str(m.tenant.id)

        # Reaching this point proves the password, so any earlier attack on the
        # account is forgiven immediately (AUD-014).
        attempts.record_success(email)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "status": user.status,
            },
            "tenants": tenants_data,
            "active_tenant": active_tenant,
        }, None

    def logout(self, refresh_token_str):
        try:
            refresh = RefreshToken(refresh_token_str)
            jti = refresh.get("jti")
            exp = refresh.get("exp")
            if jti and exp:
                BlacklistedToken.objects.get_or_create(
                    jti=jti,
                    defaults={"expires_at": dt_mod.datetime.fromtimestamp(exp, tz=dt_mod.timezone.utc)},
                )
        except Exception:
            pass


class InvitationService:
    def list_pending(self, tenant_id):
        return Invitation.objects.for_tenant(tenant_id).filter(
            accepted_at__isnull=True,
            expires_at__gte=timezone.now(),
        )

    @transaction.atomic
    def create_invitation(self, email, role, tenant_id):
        email = _email_key(email)
        if Invitation.objects.for_tenant(tenant_id).filter(
            email=email, accepted_at__isnull=True
        ).exists():
            raise ValueError("A pending invitation already exists for this email.")
        token = secrets.token_urlsafe(32)
        invitation = Invitation.objects.create(
            email=email,
            role=role,
            token=token,
            tenant_id=tenant_id,
            expires_at=timezone.now() + dt_mod.timedelta(days=7),
        )
        AuditService.record(
            action="invitation.create",
            tenant_id=tenant_id,
            target=invitation,
            after={
                "email": invitation.email,
                "role": invitation.role,
                "expires_at": invitation.expires_at.isoformat(),
            },
        )
        return invitation

    def validate_token(self, token):
        try:
            invitation = Invitation.objects.select_related("tenant").get(token=token)
        except Invitation.DoesNotExist:
            return None, "Invalid invitation token."
        if invitation.is_accepted():
            return None, "This invitation has already been accepted."
        if invitation.is_expired():
            return None, "This invitation has expired."
        return invitation, None

    @transaction.atomic
    def accept_invitation(self, token, user):
        invitation, error = self.validate_token(token)
        if error:
            return None, error
        if _email_key(user.email) != _email_key(invitation.email):
            return None, (
                "This invitation is bound to a different email address. "
                "Register with the email address it was sent to."
            )
        membership, _ = Membership.objects.get_or_create(
            user=user,
            tenant=invitation.tenant,
            defaults={"role": invitation.role},
        )
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        AuditService.record(
            action="invitation.accept",
            tenant_id=invitation.tenant_id,
            target=invitation,
            actor=user,
            after={
                "email": invitation.email,
                "role": invitation.role,
                "tenant_id": str(invitation.tenant_id),
                "accepted_at": invitation.accepted_at.isoformat(),
            },
        )
        return membership, None

    @transaction.atomic
    def cancel_invitation(self, invitation_id, tenant_id):
        invitation = (
            Invitation.objects.for_tenant(tenant_id)
            .filter(id=invitation_id, accepted_at__isnull=True)
            .first()
        )
        if invitation is None:
            raise ValueError("Invitation not found.")
        before = {"email": invitation.email, "role": invitation.role}
        invitation.delete()
        AuditService.record(
            action="invitation.cancel",
            tenant_id=tenant_id,
            target=invitation,
            before=before,
        )


class TeamService:
    def list_members(self, tenant_id):
        return Membership.objects.for_tenant(tenant_id).select_related("user")

    @transaction.atomic
    def change_role(self, tenant_id, member_user_id, new_role, requesting_user_id):
        if new_role != Membership.Role.ADMIN:
            admin_count = Membership.objects.for_tenant(tenant_id).filter(
                role=Membership.Role.ADMIN
            ).exclude(user_id=member_user_id).select_for_update().count()
            if admin_count == 0:
                raise ValueError(
                    "Cannot change the role of the last admin. Assign another admin first."
                )
        membership = Membership.objects.for_tenant(tenant_id).select_for_update().get(
            user_id=member_user_id
        )
        old_role = membership.role
        membership.role = new_role
        membership.save(update_fields=["role"])
        AuditService.record(
            action="member.role_change",
            tenant_id=tenant_id,
            target=membership,
            before={"user_id": str(membership.user_id), "role": old_role},
            after={"user_id": str(membership.user_id), "role": new_role},
        )
        return membership

    @transaction.atomic
    def remove_member(self, tenant_id, member_user_id, requesting_user_id):
        admin_count = Membership.objects.for_tenant(tenant_id).filter(
            role=Membership.Role.ADMIN
        ).exclude(user_id=member_user_id).select_for_update().count()
        if admin_count == 0:
            raise ValueError(
                "Cannot remove the last admin. Assign another admin first."
            )
        membership = Membership.objects.for_tenant(tenant_id).filter(
            user_id=member_user_id
        ).first()
        if membership is None:
            raise ValueError("Member not found.")
        before = {
            "user_id": str(membership.user_id),
            "email": membership.user.email,
            "role": membership.role,
        }
        membership.delete()
        AuditService.record(
            action="member.remove",
            tenant_id=tenant_id,
            target=membership,
            before=before,
        )

    @transaction.atomic
    def set_user_status(self, tenant_id, member_user_id, new_status, requesting_user_id):
        if new_status not in (User.Status.ACTIVE, User.Status.DISABLED):
            raise ValueError("Invalid status. Use Active or Disabled.")
        membership = (
            Membership.objects.for_tenant(tenant_id)
            .select_related("user")
            .select_for_update()
            .filter(user_id=member_user_id)
            .first()
        )
        if membership is None:
            raise Membership.DoesNotExist("Member not found.")

        target = membership.user
        if new_status == User.Status.DISABLED and target.status != User.Status.DISABLED:
            admin_count = Membership.objects.for_tenant(tenant_id).filter(
                role=Membership.Role.ADMIN
            ).exclude(user_id=member_user_id).select_for_update().count()
            if admin_count == 0:
                raise ValueError(
                    "Cannot disable the last admin. Assign another admin first."
                )

        if target.status == new_status:
            return membership

        before = {"user_id": str(target.id), "email": target.email, "status": target.status}
        target.status = new_status
        target.save(update_fields=["status"])
        action = (
            "member.disable"
            if new_status == User.Status.DISABLED
            else "member.enable"
        )
        AuditService.record(
            action=action,
            tenant_id=tenant_id,
            target=target,
            before=before,
            after={"user_id": str(target.id), "email": target.email, "status": new_status},
        )
        return membership
