# API Contracts: Accounting Schema

**Phase**: 1 — Design

**Date**: 2026-06-18

## Base URL

All endpoints are prefixed with `/api/v1/accounting/`.

## Authentication

All endpoints require a valid JWT Bearer token. The existing `BlacklistCheckingJWTAuth` authentication class applies. Tenant context is resolved from the JWT or `X-TENANT-ID` header via `TenantResolutionMiddleware`.

## Error Format

All errors follow the existing convention:

```json
{
    "detail": "Human-readable error message"
}
```

Validation errors (400 Bad Request) include field-level errors:

```json
{
    "field_name": ["Error message 1", "Error message 2"]
}
```

Authorization errors (403 Forbidden):

```json
{
    "detail": "You do not have access to this tenant."
}
```

---

## Accounts

### `GET /api/v1/accounting/accounts/`

List accounts as a flat or tree representation.

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | No | — | Filter by account type: `Asset`, `Liability`, `Equity`, `Revenue`, `Expense` |
| `tree` | boolean | No | `false` | If `true`, returns nested tree structure; if `false`, returns flat list |
| `active_only` | boolean | No | `true` | If `true`, excludes inactive accounts |

**Response 200 (flat)**:

```json
[
    {
        "id": "uuid",
        "name": "Cash",
        "type": "Asset",
        "parent_id": "uuid-or-null",
        "description": "Cash on hand and in bank",
        "is_active": true,
        "created_at": "2026-06-18T00:00:00Z"
    }
]
```

**Response 200 (tree - `?tree=true`)**:

```json
[
    {
        "id": "uuid",
        "name": "Assets",
        "type": "Asset",
        "parent_id": null,
        "children": [
            {
                "id": "uuid",
                "name": "Cash",
                "type": "Asset",
                "parent_id": "parent-uuid",
                "children": []
            }
        ]
    }
]
```

---

### `POST /api/v1/accounting/accounts/`

Create a new account.

**Request Body**:

```json
{
    "name": "Cash",
    "type": "Asset",
    "parent_id": "uuid-or-null",
    "description": "Optional description"
}
```

**Validation Rules**:

- `name` is required, max 255 characters
- `type` is required, must be one of: `Asset`, `Liability`, `Equity`, `Revenue`, `Expense`
- `parent_id` is optional; if provided, must reference an existing account in the same tenant
- Parent chain depth must not exceed 10 levels

**Response 201**:

```json
{
    "id": "uuid",
    "name": "Cash",
    "type": "Asset",
    "parent_id": null,
    "description": null,
    "is_active": true,
    "created_at": "2026-06-18T00:00:00Z",
    "updated_at": "2026-06-18T00:00:00Z"
}
```

**Response 400** (validation error):

```json
{
    "name": ["This field is required."],
    "type": ["\"InvalidType\" is not a valid choice."]
}
```

**Response 403**:

```json
{
    "detail": "You do not have accounting permissions."
}
```

---

### `GET /api/v1/accounting/accounts/{id}/`

Get a single account's details, including its immediate children.

**Response 200**:

```json
{
    "id": "uuid",
    "name": "Cash",
    "type": "Asset",
    "parent_id": "parent-uuid",
    "description": null,
    "is_active": true,
    "children": [
        {
            "id": "child-uuid",
            "name": "Petty Cash",
            "type": "Asset",
            "parent_id": "parent-uuid",
            "is_active": true
        }
    ],
    "created_at": "2026-06-18T00:00:00Z",
    "updated_at": "2026-06-18T00:00:00Z"
}
```

**Response 404**:

```json
{
    "detail": "Not found."
}
```

---

## Journal Entries

### `GET /api/v1/accounting/journal-entries/`

List journal entries, ordered by date descending.

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `date_from` | date (ISO 8601) | No | — | Start of date range filter |
| `date_to` | date (ISO 8601) | No | — | End of date range filter |
| `page` | integer | No | `1` | Page number |
| `page_size` | integer | No | `20` | Items per page |

**Response 200**:

```json
{
    "count": 50,
    "next": "http://.../journal-entries/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "date": "2026-06-18",
            "description": "Record sale of services",
            "reference": "INV-2026-001",
            "line_count": 2,
            "total_debit": "1000.0000",
            "total_credit": "1000.0000",
            "created_at": "2026-06-18T00:00:00Z"
        }
    ]
}
```

---

### `POST /api/v1/accounting/journal-entries/`

Create a new journal entry with lines.

**Request Body**:

```json
{
    "date": "2026-06-18",
    "description": "Record sale of services",
    "reference": "INV-2026-001",
    "lines": [
        {
            "account_id": "debit-account-uuid",
            "debit": "1000.0000",
            "credit": "0.0000",
            "description": "Optional line description"
        },
        {
            "account_id": "credit-account-uuid",
            "debit": "0.0000",
            "credit": "1000.0000"
        }
    ]
}
```

**Validation Rules**:

- `date` is required, must be today or earlier
- `description` is required, max 1000 characters
- `reference` is required, must be unique per tenant
- `lines` is required, must contain at least 2 items
- Each line: exactly one of `debit` or `credit` must be non-zero
- All line amounts must be non-negative
- `sum(debit)` must equal `sum(credit)` (balanced entry rule)
- All line amounts must not be zero simultaneously (FR-011)
- `account_id` must reference an existing active account in the same tenant

**Response 201**:

```json
{
    "id": "uuid",
    "date": "2026-06-18",
    "description": "Record sale of services",
    "reference": "INV-2026-001",
    "lines": [
        {
            "id": "line-uuid-1",
            "account_id": "debit-account-uuid",
            "account_name": "Cash",
            "debit": "1000.0000",
            "credit": "0.0000",
            "description": null
        },
        {
            "id": "line-uuid-2",
            "account_id": "credit-account-uuid",
            "account_name": "Revenue",
            "debit": "0.0000",
            "credit": "1000.0000",
            "description": null
        }
    ],
    "created_at": "2026-06-18T00:00:00Z"
}
```

**Response 400** (unbalanced entry):

```json
{
    "non_field_errors": ["Journal entry is not balanced. Total debits (500.00) do not equal total credits (1000.00)."]
}
```

**Response 400** (validation error):

```json
{
    "lines": [
        {"debit": ["Only one of debit or credit may be non-zero per line."]}
    ]
}
```

---

### `GET /api/v1/accounting/journal-entries/{id}/`

Get a single journal entry with all lines.

**Response 200**:

```json
{
    "id": "uuid",
    "date": "2026-06-18",
    "description": "Record sale of services",
    "reference": "INV-2026-001",
    "lines": [
        {
            "id": "line-uuid",
            "account_id": "debit-account-uuid",
            "account_name": "Cash",
            "account_type": "Asset",
            "debit": "1000.0000",
            "credit": "0.0000",
            "description": null
        }
    ],
    "created_at": "2026-06-18T00:00:00Z"
}
```

**Response 404**:

```json
{
    "detail": "Not found."
}
```

---

## Error Codes Summary

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | VALIDATION_ERROR | Field-level or non-field validation failure |
| 400 | UNBALANCED_ENTRY | Journal entry debits ≠ credits |
| 400 | REFERENCE_DUPLICATE | Journal entry reference already exists in this tenant |
| 403 | NO_ACCOUNTING_PERMISSION | User lacks accountant/admin role |
| 403 | TENANT_MISMATCH | User's tenant context does not match |
| 404 | NOT_FOUND | Resource not found |
| 409 | ACCOUNT_IN_USE | Account cannot be deleted/edited because journal entries reference it |
| 409 | ACCOUNT_HAS_CHILDREN | Account cannot be deleted because it has child accounts |
