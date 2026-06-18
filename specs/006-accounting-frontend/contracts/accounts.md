# API Contract: Accounts

Base URL: `/api/v1/accounting/accounts/`

## GET /api/v1/accounting/accounts/

List accounts (flat or tree).

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | No | Filter by type: Asset, Liability, Equity, Revenue, Expense |
| `tree` | boolean | No | If `true`, returns root accounts with nested `children` array |

### Response (flat mode)

```json
[
  {
    "id": "uuid",
    "name": "Cash",
    "type": "Asset",
    "parent_id": null,
    "description": "Cash on hand",
    "is_active": true,
    "children": [],
    "created_at": "2026-06-18T00:00:00Z",
    "updated_at": "2026-06-18T00:00:00Z"
  }
]
```

### Response (tree mode)

```json
[
  {
    "id": "uuid",
    "name": "Assets",
    "type": "Asset",
    "parent_id": null,
    "description": null,
    "is_active": true,
    "children": [
      {
        "id": "uuid",
        "name": "Cash",
        "type": "Asset",
        "parent_id": "parent-uuid",
        "description": null,
        "is_active": true,
        "children": [],
        "created_at": "2026-06-18T00:00:00Z",
        "updated_at": "2026-06-18T00:00:00Z"
      }
    ],
    "created_at": "2026-06-18T00:00:00Z",
    "updated_at": "2026-06-18T00:00:00Z"
  }
]
```

## POST /api/v1/accounting/accounts/

Create a new account.

### Request

```json
{
  "name": "Cash",
  "type": "Asset",
  "parent_id": null,
  "description": "Cash on hand"
}
```

### Response (201 Created)

Same shape as single account response above.

## GET /api/v1/accounting/accounts/{id}/

Retrieve a single account.

### Response

```json
{
  "id": "uuid",
  "name": "Cash",
  "type": "Asset",
  "parent_id": null,
  "description": "Cash on hand",
  "is_active": true,
  "children": [],
  "created_at": "2026-06-18T00:00:00Z",
  "updated_at": "2026-06-18T00:00:00Z"
}
```

## PATCH /api/v1/accounting/accounts/{id}/

Partial update an account.

### Request

```json
{
  "name": "Petty Cash",
  "description": "Updated description"
}
```

### Response (200 OK)

Updated account object.

### Error (400)

```json
{
  "type": ["Cannot change the type of an account that has been used in journal entries."]
}
```

## DELETE /api/v1/accounting/accounts/{id}/

Deactivate (soft-delete) an account.

### Response (204 No Content)

### Error (400)

```json
{
  "detail": "Cannot deactivate an account with active child accounts."
}
```
