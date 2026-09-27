import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TenantScopedQuerySet(models.QuerySet):
    def for_tenant(self, tenant_id):
        return self.filter(tenant_id=tenant_id)


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedModel(BaseModel):
    objects = TenantScopedQuerySet.as_manager()

    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.PROTECT,
    )

    class Meta:
        abstract = True


class TenantOwnedLineModel(BaseModel):
    """Line-level row that carries explicit tenant ownership (AUD-011).

    Constitution §I requires every tenant-owned table to expose ``tenant_id``.
    The line tables historically inherited ``BaseModel`` alone, so ownership
    was implied by the parent row only. The column now exists, but the parent
    stays the single source of truth: ``tenant`` is derived from the parent on
    save, and a divergent value is rejected rather than stored, so the two can
    never disagree.
    """

    objects = TenantScopedQuerySet.as_manager()

    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.PROTECT,
        related_name="+",
    )

    #: Name of the ForeignKey field that owns this line. Set by each concrete
    #: model, e.g. ``parent_field = "entry"`` for journal entry lines.
    parent_field = None

    class Meta:
        abstract = True

    @property
    def parent(self):
        return getattr(self, self.parent_field)

    def _parent_tenant_id(self):
        return getattr(self.parent, "tenant_id", None)

    def save(self, *args, **kwargs):
        parent_tenant_id = self._parent_tenant_id()
        if parent_tenant_id is not None:
            if self.tenant_id is None:
                self.tenant_id = parent_tenant_id
            elif self.tenant_id != parent_tenant_id:
                raise ValidationError(
                    f"{self._meta.verbose_name} tenant does not match its "
                    f"{self.parent_field} tenant."
                )
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        parent_tenant_id = self._parent_tenant_id()
        if (
            parent_tenant_id is not None
            and self.tenant_id is not None
            and self.tenant_id != parent_tenant_id
        ):
            raise ValidationError(
                f"{self._meta.verbose_name} tenant does not match its "
                f"{self.parent_field} tenant."
            )


class TenantQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        raise TypeError(
            "Tenants are never deleted: their accounting, inventory and audit "
            "history is permanent. Use "
            "apps.core.services.TenantDecommissionService."
        )


class Tenant(BaseModel):
    """A customer organisation, and the root of every tenant-owned row (AUD-012).

    A tenant is never deleted. ``on_delete=PROTECT`` on every tenant foreign key
    means the database refuses to take the history with it, and the model-level
    guards here stop the ORM paths that would not consult that. Retiring a
    tenant is a deliberate, recorded act instead:
    ``TenantDecommissionService`` freezes it (``status`` → ``CANCELLED``) and
    stamps who decommissioned it, when, and why.
    """

    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        SUSPENDED = "Suspended", "Suspended"
        CANCELLED = "Cancelled", "Cancelled"

    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    #: Set once, by the decommission service, and never cleared.
    decommissioned_at = models.DateTimeField(null=True, blank=True)
    decommissioned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    decommission_reason = models.TextField(blank=True, default="")

    objects = TenantQuerySet.as_manager()

    class Meta:
        db_table = "core_tenant"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"

    def __str__(self):
        return self.name

    @property
    def is_decommissioned(self):
        return self.decommissioned_at is not None

    def delete(self, *args, **kwargs):
        raise TypeError(
            "Tenants are never deleted: their accounting, inventory and audit "
            "history is permanent. Use "
            "apps.core.services.TenantDecommissionService."
        )


class AuditLogQuerySet(models.QuerySet):
    def for_tenant(self, tenant_id):
        return self.filter(tenant_id=tenant_id)

    def delete(self, *args, **kwargs):
        raise TypeError("Audit log records are immutable and cannot be deleted.")

    def update(self, *args, **kwargs):
        raise TypeError("Audit log records are immutable and cannot be updated.")


class AuditLog(models.Model):
    """Append-only, immutable audit trail (constitution §II).

    Records are created exclusively through ``apps.core.audit.AuditService``
    from the service layer. Once persisted they can be neither updated nor
    deleted through the application; ``save``, ``update``, and ``delete`` are
    guarded at the model/queryset level and no write/delete API is exposed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        db_index=True,
    )
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    action = models.CharField(max_length=100, db_index=True)
    target_type = models.CharField(max_length=64, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    before_data = models.JSONField(default=dict, blank=True)
    after_data = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        db_table = "core_audit_log"
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise ValueError("Audit log records are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Audit log records are immutable and cannot be deleted.")

    def __str__(self):
        return f"{self.action} @ {self.tenant_id} ({self.created_at})"
