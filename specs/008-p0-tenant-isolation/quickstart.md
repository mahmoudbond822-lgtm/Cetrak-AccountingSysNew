# Quickstart: P0 Tenant Isolation Validation

## Prerequisites

- Backend dependencies installed.
- Test settings available through `DJANGO_SETTINGS_MODULE=config.settings.test`.
- Test database can be created by the Django test runner.

## Run Existing Accounting Tests

From the repository root:

```powershell
Set-Location -LiteralPath "backend"
$env:DJANGO_SETTINGS_MODULE = "config.settings.test"
py -m pytest apps/accounting/tests/ -v
```

Expected outcome: all existing accounting tests pass.

## Validation Scenario 1: Cross-Tenant Parent Account Rejected

1. Create Tenant A and Tenant B.
2. Create an accounting user for each tenant.
3. Create an account in Tenant B.
4. As Tenant A, attempt to create a child account using the Tenant B account as `parent_id`.

Expected outcome: the request is rejected, no Tenant A child account is created, and the response does not disclose Tenant B account details.

## Validation Scenario 2: Cross-Tenant Journal Line Rejected

1. Create Tenant A and Tenant B.
2. Create valid accounts in both tenants.
3. As Tenant A, attempt to create a journal entry where at least one line uses a Tenant B account identifier.

Expected outcome: the request is rejected, no journal entry or line is saved, and Tenant B account details are not disclosed.

## Validation Scenario 3: Mixed-Tenant Journal Entry Leaves No Partial Records

1. Create a valid Tenant A debit account and a valid Tenant B credit account.
2. As Tenant A, submit a balanced-looking journal entry using both accounts.
3. Count Tenant A and Tenant B journal entries, ledgers, and report totals before and after the request.

Expected outcome: all counts and totals remain unchanged for both tenants.

## Validation Scenario 4: Same-Tenant Workflows Still Pass

1. As Tenant A, create a parent account.
2. As Tenant A, create a child account under that parent.
3. As Tenant A, create a balanced journal entry using only Tenant A accounts.
4. Read Tenant A accounts, journal entries, ledger, and reports.

Expected outcome: valid same-tenant workflows continue to succeed.

## Validation Scenario 5: Multi-Membership Active Tenant Boundary

1. Create a user with memberships in Tenant A and Tenant B.
2. Set the active tenant context to Tenant A.
3. Attempt to create accounting records using Tenant B account identifiers.

Expected outcome: Tenant B references are rejected while Tenant A is active, even though the user belongs to both tenants.
