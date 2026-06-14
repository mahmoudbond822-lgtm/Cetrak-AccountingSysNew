import datetime as dt_mod
import secrets

from django.contrib.auth.hashers import check_password
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Tenant
from apps.accounts.models import User, Membership, BlacklistedToken, Invitation


class AuthService:
    @transaction.atomic
    def register(self, email, password, company_name):
        if User.objects.filter(email=email).exists():
            raise ValueError("A user with this email already exists.")
        user = User.objects.create_user(email=email, password=password)
        tenant = Tenant.objects.create(name=company_name)
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role=Membership.Role.ADMIN,
        )
        refresh = RefreshToken()
        refresh["user_id"] = str(user.id)
        refresh["tenant_id"] = str(tenant.id)
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
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None, "Invalid email or password."

        if user.status == User.Status.DISABLED:
            return None, "Account has been disabled. Contact your administrator."

        if not check_password(password, user.password):
            return None, "Invalid email or password."

        memberships = Membership.objects.filter(user=user).select_related("tenant")
        tenants_data = [
            {
                "id": str(m.tenant.id),
                "name": m.tenant.name,
                "role": m.role,
            }
            for m in memberships
        ]

        refresh_lifetime = dt_mod.timedelta(days=30) if remember_me else dt_mod.timedelta(days=7)
        refresh = RefreshToken()
        refresh.set_exp(lifetime=refresh_lifetime)
        refresh["user_id"] = str(user.id)

        active_tenant = None
        if len(memberships) == 1:
            m = memberships[0]
            active_tenant = {"id": str(m.tenant.id), "name": m.tenant.name, "role": m.role}
            refresh["tenant_id"] = str(m.tenant.id)

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
        BlacklistedToken.prune_expired()


class InvitationService:
    def list_pending(self, tenant_id):
        return Invitation.objects.filter(
            tenant_id=tenant_id, accepted_at__isnull=True
        )

    @transaction.atomic
    def create_invitation(self, email, role, tenant_id):
        if Invitation.objects.filter(
            email=email, tenant_id=tenant_id, accepted_at__isnull=True
        ).exists():
            raise ValueError("A pending invitation already exists for this email.")
        token = secrets.token_urlsafe(48)
        invitation = Invitation.objects.create(
            email=email,
            role=role,
            token=token,
            tenant_id=tenant_id,
            expires_at=timezone.now() + dt_mod.timedelta(days=7),
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
        membership, _ = Membership.objects.get_or_create(
            user=user,
            tenant=invitation.tenant,
            defaults={"role": invitation.role},
        )
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        return membership, None

    @transaction.atomic
    def cancel_invitation(self, invitation_id, tenant_id):
        deleted_count = Invitation.objects.filter(
            id=invitation_id,
            tenant_id=tenant_id,
            accepted_at__isnull=True,
        ).delete()[0]
        if deleted_count == 0:
            raise ValueError("Invitation not found.")


class TeamService:
    def list_members(self, tenant_id):
        return Membership.objects.filter(tenant_id=tenant_id).select_related("user")

    def is_last_admin(self, tenant_id, exclude_user_id=None):
        qs = Membership.objects.filter(
            tenant_id=tenant_id, role=Membership.Role.ADMIN
        )
        if exclude_user_id:
            qs = qs.exclude(user_id=exclude_user_id)
        return qs.count() == 0

    @transaction.atomic
    def change_role(self, tenant_id, member_user_id, new_role, requesting_user_id):
        if new_role != Membership.Role.ADMIN and self.is_last_admin(
            tenant_id, exclude_user_id=member_user_id
        ):
            raise ValueError(
                "Cannot change the role of the last admin. Assign another admin first."
            )
        membership = Membership.objects.get(
            tenant_id=tenant_id, user_id=member_user_id
        )
        membership.role = new_role
        membership.save(update_fields=["role"])
        return membership

    @transaction.atomic
    def remove_member(self, tenant_id, member_user_id, requesting_user_id):
        if self.is_last_admin(tenant_id, exclude_user_id=member_user_id):
            raise ValueError(
                "Cannot remove the last admin. Assign another admin first."
            )
        deleted_count = Membership.objects.filter(
            tenant_id=tenant_id, user_id=member_user_id
        ).delete()[0]
        if deleted_count == 0:
            raise ValueError("Member not found.")
