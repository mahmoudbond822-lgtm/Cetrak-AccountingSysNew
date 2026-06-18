# API Contract: Journal Entries

Base URL: `/api/v1/accounting/journal-entries/`

**Note**: The `JournalEntryViewSet` exists but is NOT currently routed. Activation required in `urls.py`.

## GET /api/v1/accounting/journal-entries/

List journal entries.

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date_from` | string (ISO date) | No | Filter entries on or after this date |
| `date_to` | string (ISO date) | No | Filter entries on or before this date |

### Response

```json
[
  {
    "id": "uuid",
    "date": "2026-06-18",
    "description": "Opening balance",
    "reference": "JE-2026-001",
    "line_count": 2,
    "total_debit": "1000.0000",
    "total_credit": "1000.0000",
    "lines": [
      {
        "id": "uuid",
        "account_id": "uuid",
        "account_name": "Cash",
        "account_type": "Asset",
        "debit": "1000.0000",
        "credit": "0.0000",
        "description": "Initial deposit"
      },
      {
        "id": "uuid",
        "account_id": "uuid",
        "account_name": "Owner's Equity",
        "account_type": "Equity",
        "debit": "0.0000",
        "credit": "1000.0000",
        "description": "Initial contribution"
      }
    ],
    "created_at": "2026-06-18T00:00:00Z"
  }
]
```

## POST /api/v1/accounting/journal-entries/

Create a new journal entry.

### Request

```json
{
  "date": "2026-06-18",
  "description": "Opening balance",
  "reference": "JE-2026-001",
  "lines": [
    {
      "account_id": "uuid",
      "debit": "1000.0000",
      "credit": "0.0000",
      "description": "Initial deposit"
    },
    {
      "account_id": "uuid",
      "debit": "0.0000",
      "credit": "1000.0000",
      "description": "Initial contribution"
    }
  ]
}
```

### Response (201 Created)

Full journal entry object as above.

### Validation Errors (400)

```json
{
  "lines": ["A journal entry must have at least 2 lines."]
}
```

```json
{
  "non_field_errors": ["Journal entry is not balanced. Total debits (100.0000) do not equal total credits (200.0000)."]
}
```

## GET /api/v1/accounting/journal-entries/{id}/

Retrieve a single journal entry.

### Response

Full journal entry object as above.

## PUT/PATCH /api/v1/accounting/journal-entries/{id}/

### Response (405 Method Not Allowed)

```json
{
  "detail": "Journal entries are immutable and cannot be modified."
}
```

## DELETE /api/v1/accounting/journal-entries/{id}/

### Response (405 Method Not Allowed)

```json
{
  "detail": "Journal entries are immutable and cannot be deleted."
}
```
