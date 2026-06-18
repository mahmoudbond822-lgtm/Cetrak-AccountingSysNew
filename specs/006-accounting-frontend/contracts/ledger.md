# API Contract: Ledger

Base URL: `/api/v1/accounting/ledger/`

**Note**: This endpoint needs to be implemented — it does not exist yet.

## GET /api/v1/accounting/ledger/

Get ledger entries for a specific account.

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `account_id` | UUID | Yes | Account to show ledger for |
| `date_from` | string (ISO date) | No | Start of date range |
| `date_to` | string (ISO date) | No | End of date range |

### Response

```json
{
  "account": {
    "id": "uuid",
    "name": "Cash",
    "type": "Asset"
  },
  "entries": [
    {
      "date": "2026-06-18",
      "description": "Opening balance",
      "reference": "JE-2026-001",
      "debit": "1000.0000",
      "credit": "0.0000",
      "running_balance": "1000.0000"
    },
    {
      "date": "2026-06-19",
      "description": "Office supplies",
      "reference": "JE-2026-002",
      "debit": "0.0000",
      "credit": "200.0000",
      "running_balance": "800.0000"
    }
  ],
  "totals": {
    "total_debit": "1000.0000",
    "total_credit": "200.0000",
    "closing_balance": "800.0000"
  }
}
```

### Error (404)

```json
{
  "detail": "Account not found."
}
```
