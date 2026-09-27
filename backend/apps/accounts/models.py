import uuid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from datetime import timedelta
from django.utils import timezone

from apps.core.models import TenantScopedModel, TenantScopedQuerySet


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("status", User.Status.ACTIVE)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        INVITED = "Invited", "Invited"
        DISABLED = "Disabled", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email


class Membership(models.Model):
    objects = TenantScopedQuerySet.as_manager()

    class Role(models.TextChoices):
        ADMIN = "Admin", "Admin"
        ACCOUNTANT = "Accountant", "Accountant"
        MANAGER = "Manager", "Manager"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    # PROTECT (AUD-012): the membership record is part of the evidence trail for
    # a tenant, so it dies with the *user*, never with the tenant. Losing a tenant
    # must never silently erase who had access to what.
    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.PROTECT,
        related_name="memberships",
        db_index=True,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ACCOUNTANT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_membership"
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tenant"],
                name="unique_user_tenant_membership",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} @ {self.tenant.name} ({self.role})"


class BlacklistedToken(models.Model):
    jti = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_blacklisted_token"
        verbose_name = "Blacklisted Token"
        verbose_name_plural = "Blacklisted Tokens"
        indexes = [
            models.Index(fields=["jti"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    @classmethod
    def prune_expired(cls):
        cls.objects.filter(expires_at__lte=timezone.now()).delete()


class Invitation(TenantScopedModel):
    class Role(models.TextChoices):
        ACCOUNTANT = "Accountant", "Accountant"
        MANAGER = "Manager", "Manager"

    email = models.EmailField(max_length=254)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ACCOUNTANT,
    )
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_invitation"
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["email"]),
            models.Index(fields=["tenant"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["email", "tenant"],
                name="unique_pending_invitation_per_tenant",
            ),
        ]

    def __str__(self):
        return f"Invitation for {self.email} @ {self.tenant_id} ({self.role})"

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_accepted(self):
        return self.accepted_at is not None
