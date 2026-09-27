"""Tenant decommission: the only supported way to retire a tenant (AUD-012).

``core.Tenant`` is the root of every tenant-owned table. Its foreign keys are
``on_delete=PROTECT`` and the model refuses ``delete()``, so accounting,
inventory, sales, purchases and audit history cannot be destroyed by dropping a
row — the historical failure mode this replaces, where a single ``Tenant.delete()``
silently wiped ~25 tables with no archive and no record that it had happened.

Retiring a customer is a deliberate, recorded act instead:

* ``status`` becomes ``CANCELLED``, which the permission layer already treats as
  no-access (``TenantScopedPermission`` requires ``ACTIVE``), so the tenant is
  frozen at once;
* ``decommissioned_at`` / ``decommissioned_by`` / ``decommission_reason`` record
  who did it and why, permanently and exactly once;
* an immutable audit row is appended with the before/after state.

Nothing is purged. Erasure of personal data on request is deliberately **not**
implemented here — see ``docs/audits/AUD-012-implementation-report.md``.

This is a service-layer API only: no HTTP endpoint is exposed, so there is no new
public surface and no new permission to design. It is called by an operator (a
shell or a management task) acting as a tenant admin.
"""

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Membership
from apps.core.audit import AuditService
from apps.core.models import Tenant

#: Long enough to record why a customer left, short enough that an audit row
#: stays readable. Overflow is truncated rather than rejected so a verbose
#: incident note can never block a decommission that is already justified.
MAX_REASON_LENGTH = 2000

ACTION_DECOMMISSION = "tenant.decommission"


class TenantDecommissionService:
    """Decommission (freeze + record) a single tenant."""

    @staticmethod
    def decommission(*, tenant, actor, reason):
        """Retire ``tenant``: freeze it and record who did it and why.

        Args:
            tenant: the :class:`~apps.core.models.Tenant` to retire.
            actor: the :class:`~apps.accounts.models.User` performing the
                decommission. Must hold ``Membership.Role.ADMIN`` on that
                tenant. There is no platform-superuser role in this data model
                (``User`` carries no ``is_superuser``), so an operator who is not
                a member of the tenant adds a membership first, exactly as for
                every other privileged action here.
            reason: why the tenant is being retired. Required, because a
                decommission without a stated reason is indistinguishable from
                data loss once the tenant can no longer be inspected.

        Returns:
            The saved :class:`~apps.core.models.Tenant`.

        Raises:
            ValueError: if the reason is blank, the tenant is already
                decommissioned, or the actor is not an admin of the tenant.
        """
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("A decommission reason is required.")
        reason = reason[:MAX_REASON_LENGTH]

        if actor is None:
            raise ValueError("A decommission requires an identified actor.")

        with transaction.atomic():
            # Re-read under the transaction so two concurrent operators cannot
            # both pass the guard and both write a decommission stamp.
            tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)

            # Authorization first: a non-admin must not be able to learn whether
            # or when this tenant was decommissioned by provoking the error.
            if not TenantDecommissionService._may_decommission(
                actor=actor, tenant=tenant
            ):
                raise ValueError("Only an admin of the tenant may decommission it.")

            if tenant.is_decommissioned:
                raise ValueError(
                    f"Tenant {tenant.name} was already decommissioned at "
                    f"{tenant.decommissioned_at.isoformat()}."
                )

            before = {"status": tenant.status}
            tenant.status = Tenant.Status.CANCELLED
            tenant.decommissioned_at = timezone.now()
            tenant.decommissioned_by = actor
            tenant.decommission_reason = reason
            tenant.save(
                update_fields=[
                    "status",
                    "decommissioned_at",
                    "decommissioned_by",
                    "decommission_reason",
                    "updated_at",
                ]
            )

            AuditService.record(
                action=ACTION_DECOMMISSION,
                tenant_id=tenant.pk,
                target=tenant,
                actor=actor,
                before=before,
                after={
                    "status": tenant.status,
                    "decommissioned_at": tenant.decommissioned_at,
                    "decommissioned_by": str(actor.pk),
                },
                metadata={"reason": reason},
            )

        return tenant

    @staticmethod
    def _may_decommission(*, actor, tenant):
        """Only a tenant admin may retire the tenant, as for any admin action."""
        return Membership.objects.filter(
            user=actor,
            tenant=tenant,
            role=Membership.Role.ADMIN,
        ).exists()
