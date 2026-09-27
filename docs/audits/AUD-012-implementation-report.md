# AUD-012 — Tenant Decommission Workflow

**Status:** implemented
**Audit item:** AUD-012 (P1) — "Tenant hard-delete cascade can destroy all tenant data without archiving"
**Baseline commit:** `a70405d`
**Branch:** `014-auto-customer-code`

---

## 1. The finding

`docs/audits/AUD-003-final-production-readiness-reaudit.md:75,192,236` recorded that
`core.Tenant` was the root of ~25 tenant-owned tables and that every tenant foreign key
used `on_delete=CASCADE`. A single `Tenant.delete()` would therefore take an entire
customer's accounting, inventory, sales, purchases and access history with it, leaving
no archive and no record that it had happened.

Two mitigating facts were re-verified against the code, and both are true:

- **There is no tenant-delete API and no tenant registered in Django admin.** The
  endpoint does not exist, so the cascade is a latent trap for a future view, a
  management command or a shell, not a live vulnerability today.
- **Nothing in the codebase calls `Tenant.delete()`.** The only `TransactionTestCase`
  teardown is the standard `TransactionTestCase._fixture_teardown`, which flushes the
  database and never goes through the ORM's delete collector.

The finding was still worth closing: a guard that does not exist is not a control, and
the blast radius if one is ever added is the whole customer dataset.

A second, smaller gap was found while tracing the consequences. `Tenant.Status` already
distinguishes `ACTIVE` / `SUSPENDED` / `CANCELLED`, and `TenantScopedPermission` already
denies API access to a non-`ACTIVE` tenant. But `accounts.views.refresh_view` only
checked the *user's* status. A refresh token minted for a tenant-bound session therefore
kept rotating for a suspended or cancelled tenant: harmless for data access, but it left
the lock-out incomplete and burned a blacklisted-token row on every rotation.

## 2. The decision

Retiring a customer is a deliberate, recorded act. Nothing is ever purged, because
accounting records are not the tenant's to erase and the audit trail must outlive the
party it describes. Four choices were put to the user and confirmed:

| Choice | Decision |
| --- | --- |
| Purge vs retain | **Retain.** `PROTECT` everywhere, no purge path, no erasure endpoint. |
| Surface | **Service only.** No HTTP endpoint, no permission to design, no frontend. |
| Status | **Reuse `CANCELLED`** plus decommission stamps. No new status. |
| Sessions | **Refuse refresh** for a non-`ACTIVE` tenant. |

## 3. What was built

### 3.1 History cannot be cascaded away

`on_delete` on `TenantScopedModel.tenant` and `TenantOwnedLineModel.tenant` moved from
`CASCADE` to `PROTECT`, and `accounts.Membership.tenant` likewise. Because those bases are
abstract, the change propagates to every concrete model in all five apps, and the
generated migrations record it in 22 fields.

`on_delete` is ORM collector behaviour, not a database constraint. Django never emitted
`ON DELETE CASCADE` to PostgreSQL, confirmed on the live dev database:

```
journalentry.tenant FK delete action -> ['a']   (a = no action)
```

So a raw `DELETE FROM core_tenant` was already refused by PostgreSQL, while the ORM path
would have cascaded. The defect was in the ORM path, and that is the path now closed.

`core.AuditLog.tenant` stays `SET_NULL` on purpose: an audit row must be able to outlive
the thing it describes. It is the single exemption, and it is named in the invariant test
rather than left implicit.

### 3.2 Deletion is refused, and says why

`Tenant.delete()` and `TenantQuerySet.delete()` both raise `TypeError` pointing at the
service. These are belt *and* braces: the collector test calls
`Collector(using="default")` directly, bypassing both guards, and still gets
`ProtectedError`. The protection is structural, not a single check some other code path
could route around.

### 3.3 `TenantDecommissionService`

`backend/apps/core/services.py` is the only supported way to retire a tenant. It:

1. requires a non-blank reason, trimmed and capped at `MAX_REASON_LENGTH` (2000) so a
   verbose incident note can never block an already-justified decommission;
2. requires an identified actor;
3. re-reads the tenant with `select_for_update()` inside the transaction, so two
   concurrent operators cannot both pass the guard;
4. **authorizes before it discloses anything** — a non-admin gets the authorization
   error, never the "already decommissioned at `<timestamp>`" one;
5. sets `status = CANCELLED` and the three stamps (`decommissioned_at`,
   `decommissioned_by`, `decommission_reason`) in a single `save()`;
6. appends one immutable `AuditService.record(action="tenant.decommission")` row with the
   before/after state and the reason.

Because `CANCELLED` is already a no-access status, the tenant is frozen the moment the
transaction commits, and it stays frozen however often the token is refreshed.

**Authorization is tenant-scoped admin only.** This codebase has no platform-superuser
role: `User` extends `AbstractBaseUser` and carries no `is_superuser` or `is_staff`
column, so `create_superuser()` cannot create one. An operator who is not a member of
the tenant adds a membership first, exactly as for every other privileged action. This
was confirmed with the user after the originally-approved "admin or superuser" rule
turned out to be unimplementable as written; the dead `is_superuser` branch was removed
rather than left in as untestable code.

### 3.4 The decommission stamp is the permanent record

`status` remains a plain mutable field, so an operator can still flip it back with a
`save()`. The guarantee that a tenant *was* decommissioned therefore comes from the stamp,
not from the current status, and a test pins that.

### 3.5 Sessions stop

`refresh_view` now resolves the token's `tenant_id` claim and returns **403
`This session's organization is no longer active.`** before blacklisting or minting
anything. The denial is stable and repeatable rather than one-shot, and a token with no
`tenant_id` claim (a multi-tenant login, which issues an unbound refresh) is untouched.

## 4. Defect found and fixed on the way: `accounting/0005`

Applying the migrations to a real PostgreSQL database exposed a **deploy blocker in
already-committed code** (`2b08f5a`, the AUD-030 stream):

```
apps/accounting/migrations/0005_decimal_exact_balance_check.py:39
    unbalanced = schema_editor.execute(COUNT_UNBALANCED).fetchone()[0]
AttributeError: 'NoneType' object has no attribute 'fetchone'
```

Django 6's `BaseDatabaseSchemaEditor.execute()` executes inside its own
`with connection.cursor()` and returns `None`; the `return cursor` this code depended on
is gone. **Every `migrate` against PostgreSQL failed at this node**, including on a fresh
production database.

It had never been caught because `config/settings/test.py` falls back to in-memory SQLite
unless all four `POSTGRES_*` variables are set, and the migration returns early for
`vendor != "postgresql"`. Its PostgreSQL branch had therefore never executed anywhere, and
the migration check in the previous report was SQLite-only.

Fixed in `8181ccd` on its own commit, before any AUD-012 code: the count is read from an
explicit cursor, and the tests now *call* `apply_exact_check` and `restore_tolerant_check`
with a stand-in schema editor mirroring the Django 6 contract, covering the success path,
the refusal path, the non-PostgreSQL no-op and the reverse. The new tests were confirmed
to fail against the previous code.

**This is a systemic gap, not a one-off:** a suite that defaults to SQLite cannot see
PostgreSQL-only code, and this project has Postgres-only SQL. See §6.

## 5. Verification

| Gate | Result |
| --- | --- |
| `pytest apps/ -q` (SQLite, the default) | **601 passed, 6 skipped, 25 subtests** |
| `pytest apps/ -q` (**real PostgreSQL 15**) | **602 passed, 5 skipped, 25 subtests** |
| `makemigrations --check --dry-run` | No changes detected |
| `migrate` on the live dev database | all migrations applied, including the six new ones |
| `sqlmigrate` on the `CASCADE`→`PROTECT` flips | `(no-op)` — state-only, no data touched |
| `npm run build` | clean — 444.15 kB JS / 123.75 kB gzip, 11.67 kB CSS |
| `npm run lint` | 13 problems (12 errors, 1 warning) — unchanged baseline, all pre-existing |
| `git diff --check` | clean |

The PostgreSQL run is the one that matters most, and it was impossible before this
stream: the test database was built from zero by running every migration in order, so
`accounting/0005` and all six AUD-012 migrations executed against PostgreSQL for the first
time. The one extra passing test is `test_sales_inventory_api.py:291`, which is
vendor-gated and therefore inert on SQLite.

Baseline before this stream was 572 passed / 6 skipped / 16 subtests. The 29 new tests are
21 in `apps/core/tests/test_tenant_decommission.py` (9 of them subtests), 5 in
`apps/accounts/tests/test_status_enforcement.py`, and 4 in
`apps/accounting/tests/test_decimal_exact_balance_constraint.py`. No test was weakened or
deleted.

New tests cover, among others: every tenant FK in every app is `PROTECT` or explicitly
exempted; the exemption is still what it claims to be; the invariant is not vacuous;
model, queryset and collector deletion all refuse; freeze/stamp/audit happen atomically;
exactly one audit row with the right before/after; history survives; a non-admin, an
outsider and an admin of *another* tenant are all refused; reason required, truncated,
actor required, once only; the stamp outlives a status edit; the audit row cannot be
rewritten or deleted; and refresh is refused for suspended and decommissioned tenants,
repeatably, while active and unbound tokens still work.

## 6. Follow-ups (not done here)

1. **The suite has no PostgreSQL by default.** `config/settings/test.py` falls back to
   SQLite, which silently disconnects every Postgres-only code path — a migration
   function, a `CHECK` constraint, a partial index, `JSONB` behaviour. This is exactly
   what hid the `accounting/0005` blocker through an entire green stream. Consider making
   PostgreSQL the default in CI, or gating a PG job.
2. **`User` has no staff or superuser role** (`AbstractBaseUser`, no `is_superuser`), and
   `UserManager.create_superuser` does not set one because the column does not exist. Any
   future cross-tenant operator action has the same dead-end this stream hit. Left alone
   as out of scope; flagged rather than fixed.
3. **No purge/erasure path exists**, by decision. A GDPR-style erasure request would need
   a designed, auditable procedure that anonymizes personal data while preserving
   accounting records. Not attempted.
4. **The decommission is service-only**, so it is currently operator-invoked from a shell
   or management task. A future management command should call the same service; the
   guards in §3.2 mean a careless `delete` cannot be substituted for it.
5. `test_cetrak_test` could not be dropped at the end of the PostgreSQL run ("2 other
   sessions using the database"). The database was in a disposable container, so nothing
   leaked, but something holds a connection past teardown and is worth a look.
