"""AUD-012: a tenant can be retired, never deleted.

Two layers are covered here. First the structural invariant: every foreign key
that points at a tenant must be ``PROTECT``, in every app, so no new model can
reintroduce the cascade that used to take a customer's history with it. Then the
behaviour: the ORM refuses to delete a tenant, the collector refuses even when
the model guard is bypassed, and the decommission service freezes the tenant and
records who did it and why.
"""

from datetime import timedelta

from django.apps import apps
from django.db import models
from django.db.models.deletion import Collector, ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Invitation, Membership, User
from apps.accounting.models import Account
from apps.core.models import AuditLog, Tenant
from apps.core.services import (
    ACTION_DECOMMISSION,
    MAX_REASON_LENGTH,
    TenantDecommissionService,
)
from apps.inventory.models import Product
from apps.purchases.models import Vendor
from apps.sales.models import Customer


REASON = "Customer moved to another provider."

#: Sentinel so a test can pass ``actor=None`` on purpose without the helper
#: substituting the default admin for it.
NOT_GIVEN = object()

#: ``AuditLog.tenant`` is ``SET_NULL`` on purpose and is the one tenant foreign
#: key that is not ``PROTECT``: an audit row must be able to outlive the thing it
#: describes. It is listed here so that a *new* cascade anywhere else still fails
#: the invariant test below, and so the exemption is deliberate rather than
#: invisible.
TENANT_FK_EXEMPTIONS = {"core.AuditLog.tenant": models.SET_NULL}


def _tenant_fk_fields():
    """Every loaded model field that is a single foreign key to ``core.Tenant``."""
    tenant_model = apps.get_model("core", "Tenant")
    return [
        (model, field)
        for model in apps.get_models()
        for field in model._meta.get_fields()
        if getattr(field, "many_to_one", False)
        and field.remote_field.model is tenant_model
    ]


class TenantForeignKeyProtectionTests(TestCase):
    """The invariant, checked across every model rather than a hand-picked few."""

    def test_every_tenant_foreign_key_is_protect_or_explicitly_exempted(self):
        offending = [
            f"{model._meta.label}.{field.name}"
            for model, field in _tenant_fk_fields()
            if field.remote_field.on_delete is not models.PROTECT
            and f"{model._meta.label}.{field.name}" not in TENANT_FK_EXEMPTIONS
        ]
        self.assertEqual(
            offending,
            [],
            f"tenant foreign keys that would delete history: {offending}",
        )

    def test_the_exemptions_still_are_what_they_claim_to_be(self):
        found = {
            f"{model._meta.label}.{field.name}": field.remote_field.on_delete
            for model, field in _tenant_fk_fields()
            if f"{model._meta.label}.{field.name}" in TENANT_FK_EXEMPTIONS
        }
        self.assertEqual(found, TENANT_FK_EXEMPTIONS)

    def test_the_invariant_is_not_vacuous(self):
        labels = {model._meta.label for model, _ in _tenant_fk_fields()}
        for expected in (
            "accounting.Account",
            "accounts.Membership",
            "inventory.Product",
            "purchases.Vendor",
            "sales.Customer",
        ):
            self.assertIn(expected, labels)


class TenantDeleteRefusalTests(TestCase):
    """``Tenant.delete()`` is a bug, and says so."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme")

    def test_model_delete_raises_and_keeps_the_tenant(self):
        with self.assertRaises(TypeError) as caught:
            self.tenant.delete()

        self.assertIn("never deleted", str(caught.exception))
        self.assertIn("TenantDecommissionService", str(caught.exception))
        self.assertTrue(Tenant.objects.filter(pk=self.tenant.pk).exists())

    def test_queryset_delete_raises(self):
        with self.assertRaises(TypeError):
            Tenant.objects.filter(pk=self.tenant.pk).delete()

    def test_queryset_delete_of_every_tenant_raises(self):
        Tenant.objects.create(name="Globex")

        with self.assertRaises(TypeError):
            Tenant.objects.all().delete()

        self.assertEqual(Tenant.objects.count(), 2)

    def test_collector_refuses_even_when_the_model_guard_is_bypassed(self):
        """The guard is belt *and* braces: ``on_delete=PROTECT`` is the real fence.

        ``Collector`` is what ``QuerySet.delete()`` uses internally. Calling it
        directly skips :meth:`Tenant.delete` and the queryset override, so this
        asserts the protection is structural rather than a single check that some
        other code path could route around.
        """
        cases = {
            "accounting.Account": lambda t: Account.objects.create(
                tenant=t, name="Cash", type=Account.Type.ASSET
            ),
            "inventory.Product": lambda t: Product.objects.create(
                tenant=t, sku="SKU-1", name="Widget", unit="each"
            ),
            "sales.Customer": lambda t: Customer.objects.create(
                tenant=t, code="C-1", name="Client"
            ),
            "purchases.Vendor": lambda t: Vendor.objects.create(
                tenant=t, code="V-1", name="Supplier"
            ),
            "accounts.Membership": lambda t: Membership.objects.create(
                tenant=t,
                user=User.objects.create_user(
                    email=f"member{t.pk.hex[:6]}@example.com", password="SecurePass123"
                ),
                role=Membership.Role.ADMIN,
            ),
            "accounts.Invitation": lambda t: Invitation.objects.create(
                tenant=t,
                email=f"invited{t.pk.hex[:6]}@example.com",
                role=Membership.Role.ACCOUNTANT,
                token=f"token-{t.pk.hex[:8]}",
                expires_at=timezone.now() + timedelta(days=1),
            ),
        }

        for label, create_row in cases.items():
            with self.subTest(model=label):
                tenant = Tenant.objects.create(name=f"Tenant of {label}")
                create_row(tenant)

                with self.assertRaises(ProtectedError):
                    collector = Collector(using="default")
                    collector.collect([tenant])
                    collector.delete()

                self.assertTrue(Tenant.objects.filter(pk=tenant.pk).exists())


class TenantDecommissionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme")
        self.admin = User.objects.create_user(
            email="admin@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.admin, tenant=self.tenant, role=Membership.Role.ADMIN
        )
        self.accountant = User.objects.create_user(
            email="bookkeeper@example.com", password="SecurePass123"
        )
        Membership.objects.create(
            user=self.accountant, tenant=self.tenant, role=Membership.Role.ACCOUNTANT
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com", password="SecurePass123"
        )
        self.audit_rows = AuditLog.objects.filter(action=ACTION_DECOMMISSION)

    def _decommission(self, *, tenant=None, actor=NOT_GIVEN, reason=REASON):
        return TenantDecommissionService.decommission(
            tenant=tenant or self.tenant,
            actor=self.admin if actor is NOT_GIVEN else actor,
            reason=reason,
        )

    def test_it_freezes_the_tenant_and_records_who_and_why(self):
        assert not self.tenant.is_decommissioned
        before = timezone.now()

        self._decommission()

        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, Tenant.Status.CANCELLED)
        self.assertTrue(self.tenant.is_decommissioned)
        self.assertEqual(self.tenant.decommissioned_by, self.admin)
        self.assertEqual(self.tenant.decommission_reason, REASON)
        self.assertGreaterEqual(self.tenant.decommissioned_at, before)

    def test_it_writes_exactly_one_audit_row_with_the_transition(self):
        self._decommission()

        self.assertEqual(self.audit_rows.count(), 1)
        row = self.audit_rows.get()
        self.assertEqual(row.tenant_id, self.tenant.pk)
        self.assertEqual(row.actor, self.admin)
        self.assertEqual(row.target_type, "core.tenant")
        self.assertEqual(row.target_id, str(self.tenant.pk))
        self.assertEqual(row.before_data, {"status": Tenant.Status.ACTIVE})
        self.assertEqual(row.after_data["status"], Tenant.Status.CANCELLED)
        self.assertEqual(row.after_data["decommissioned_by"], str(self.admin.pk))
        self.assertEqual(row.metadata["reason"], REASON)

    def test_it_leaves_the_history_in_place(self):
        account = Account.objects.create(
            tenant=self.tenant, name="Cash", type=Account.Type.ASSET
        )

        self._decommission()

        self.assertTrue(Account.objects.filter(pk=account.pk).exists())
        self.assertEqual(Membership.objects.filter(tenant=self.tenant).count(), 2)

    def test_an_admin_of_another_tenant_may_not(self):
        """Authorization is per-tenant: an admin elsewhere gets no special pass."""
        elsewhere = Tenant.objects.create(name="Globex")
        Membership.objects.create(
            user=self.outsider, tenant=elsewhere, role=Membership.Role.ADMIN
        )

        with self.assertRaises(ValueError) as caught:
            self._decommission(actor=self.outsider)

        self.assertIn("admin of the tenant", str(caught.exception))
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_decommissioned)
        self.assertEqual(self.audit_rows.count(), 0)

    def test_an_admin_of_the_tenant_may(self):
        self._decommission(actor=self.admin)

        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.decommissioned_by, self.admin)

    def test_a_non_admin_member_may_not(self):
        with self.assertRaises(ValueError) as caught:
            self._decommission(actor=self.accountant)

        self.assertIn("admin of the tenant", str(caught.exception))
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_decommissioned)
        self.assertEqual(self.audit_rows.count(), 0)

    def test_a_user_with_no_membership_may_not(self):
        with self.assertRaises(ValueError):
            self._decommission(actor=self.outsider)

        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_decommissioned)

    def test_a_reason_is_required(self):
        for reason in ("", "   ", None):
            with self.subTest(reason=reason):
                with self.assertRaises(ValueError) as caught:
                    self._decommission(reason=reason)
                self.assertIn("reason is required", str(caught.exception))

        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_decommissioned)
        self.assertEqual(self.audit_rows.count(), 0)

    def test_an_oversized_reason_is_truncated_rather_than_refused(self):
        self._decommission(reason="x" * (MAX_REASON_LENGTH + 500))

        self.tenant.refresh_from_db()
        self.assertEqual(len(self.tenant.decommission_reason), MAX_REASON_LENGTH)
        self.assertEqual(
            self.audit_rows.get().metadata["reason"], "x" * MAX_REASON_LENGTH
        )

    def test_it_requires_an_identified_actor(self):
        with self.assertRaises(ValueError) as caught:
            self._decommission(actor=None)

        self.assertIn("identified actor", str(caught.exception))
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_decommissioned)

    def test_it_happens_at_most_once(self):
        self._decommission()
        self.tenant.refresh_from_db()
        first_at = self.tenant.decommissioned_at
        first_by = self.tenant.decommissioned_by

        with self.assertRaises(ValueError) as caught:
            self._decommission()

        self.assertIn("already decommissioned", str(caught.exception))
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.decommissioned_at, first_at)
        self.assertEqual(self.tenant.decommissioned_by, first_by)
        self.assertEqual(self.audit_rows.count(), 1)

    def test_a_non_admin_cannot_learn_the_decommission_state_from_the_error(self):
        """Authorization is checked first, so the guard leaks nothing.

        The order of these two checks is a deliberate choice: a non-admin who
        provokes a decommission on an already-retired tenant gets the
        authorization error, not the "already decommissioned at <timestamp>" one.
        """
        self._decommission()

        with self.assertRaises(ValueError) as caught:
            self._decommission(actor=self.accountant)

        self.assertIn("admin of the tenant", str(caught.exception))
        self.assertNotIn("already decommissioned", str(caught.exception))

    def test_the_stamp_survives_a_later_status_edit(self):
        """The stamp is the permanent record; ``status`` is the mutable lever.

        Nothing in the service stops an operator flipping ``status`` back with a
        plain ``save()``, so the guarantee that a tenant *was* decommissioned has
        to come from the stamp rather than from the current status.
        """
        self._decommission()
        Tenant.objects.filter(pk=self.tenant.pk).update(
            status=Tenant.Status.ACTIVE
        )

        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.is_decommissioned)
        self.assertEqual(self.tenant.decommissioned_by, self.admin)

    def test_the_audit_row_cannot_be_rewritten_or_removed(self):
        self._decommission()
        row = self.audit_rows.get()
        row.action = "tampered"

        with self.assertRaises(ValueError):
            row.save()
        with self.assertRaises(TypeError):
            row.delete()

        survivor = self.audit_rows.get()
        self.assertEqual(survivor.action, ACTION_DECOMMISSION)
        self.assertEqual(survivor.metadata["reason"], REASON)
        self.assertEqual(survivor.after_data["status"], Tenant.Status.CANCELLED)
