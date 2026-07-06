# Contract: Accounting API Tenant Isolation

This contract documents the user-visible accounting API behavior required by the P0 tenant isolation feature.

## Active Tenant Context

All accounting requests are evaluated in the caller's active tenant context. A record identifier is valid only when the record belongs to that active tenant and the caller has accounting access for that tenant.

## Create Account

**Interface**: `POST /api/v1/accounting/accounts/`

**Relevant Input**:

- `name`: Account name
- `type`: Account type
- `parent_id`: Optional parent account identifier
- `description`: Optional description

**Required Behavior**:

- If `parent_id` is omitted, normal root account creation rules apply.
- If `parent_id` belongs to the active tenant, the child account may be created when all other account rules pass.
- If `parent_id` is unknown or inaccessible to the active tenant, the request must fail.
- A failed parent reference must not create an account.
- The failure response must not reveal the inaccessible account's name, type, balance, transaction history, tenant, or existence.

## Create Journal Entry

**Interface**: `POST /api/v1/accounting/journal-entries/`

**Relevant Input**:

- `date`: Accounting date
- `description`: Entry description
- `reference`: Tenant-specific reference
- `lines`: Two or more journal lines
- `lines[].account_id`: Account identifier for each line
- `lines[].debit`: Debit amount when applicable
- `lines[].credit`: Credit amount when applicable
- `lines[].description`: Optional line description

**Required Behavior**:

- Each `lines[].account_id` must belong to the active tenant.
- If every referenced account belongs to the active tenant and the entry satisfies existing accounting rules, the journal entry may be created.
- If any line references an unknown or inaccessible account, the whole request must fail.
- A failed request must not create a journal entry header, journal line, balance movement, ledger row, or report-impacting record.
- The failure response must not reveal inaccessible account details.

## Read Accounting Records

**Interfaces**:

- `GET /api/v1/accounting/accounts/`
- `GET /api/v1/accounting/accounts/{id}/`
- `GET /api/v1/accounting/journal-entries/`
- `GET /api/v1/accounting/ledger/`
- `GET /api/v1/accounting/reports/`

**Required Behavior**:

- Read interfaces must continue to return only records belonging to the active tenant.
- Attempts to retrieve another tenant's accounting record must not expose that record.

## Acceptance Matrix

| Scenario | Expected Result |
|----------|-----------------|
| Tenant A creates child account under Tenant A parent | Success when other account rules pass |
| Tenant A creates child account under Tenant B parent | Rejected; no account created |
| Tenant A creates journal entry using only Tenant A accounts | Success when existing journal rules pass |
| Tenant A creates journal entry using a Tenant B account | Rejected; no entry or line created |
| Tenant A creates journal entry with one Tenant A account and one Tenant B account | Rejected; no partial records created |
| User belongs to Tenant A and Tenant B but active tenant is Tenant A | Only Tenant A account references are accepted |
