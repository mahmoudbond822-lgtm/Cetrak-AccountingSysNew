# API Contract: Reports

Base URL: `/api/v1/accounting/reports/`

**Note**: These endpoints need to be implemented — they do not exist yet.

## GET /api/v1/accounting/reports/trial-balance/

Get trial balance for a date range.

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date_from` | string (ISO date) | No | Start of period |
| `date_to` | string (ISO date) | No | End of period (defaults to today) |

### Response

```json
{
  "report_type": "trial-balance",
  "date_from": "2026-01-01",
  "date_to": "2026-12-31",
  "rows": [
    {
      "account_id": "uuid",
      "account_name": "Cash",
      "account_type": "Asset",
      "debit": "50000.0000",
      "credit": "0.0000"
    },
    {
      "account_id": "uuid",
      "account_name": "Accounts Payable",
      "account_type": "Liability",
      "debit": "0.0000",
      "credit": "15000.0000"
    }
  ],
  "totals": {
    "total_debit": "50000.0000",
    "total_credit": "50000.0000"
  }
}
```

## GET /api/v1/accounting/reports/income-statement/

Get income statement for a date range.

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date_from` | string (ISO date) | No | Start of period |
| `date_to` | string (ISO date) | No | End of period (defaults to today) |

### Response

```json
{
  "report_type": "income-statement",
  "date_from": "2026-01-01",
  "date_to": "2026-12-31",
  "revenues": [
    {
      "account_id": "uuid",
      "account_name": "Sales Revenue",
      "balance": "100000.0000"
    }
  ],
  "total_revenue": "100000.0000",
  "expenses": [
    {
      "account_id": "uuid",
      "account_name": "Rent Expense",
      "balance": "12000.0000"
    },
    {
      "account_id": "uuid",
      "account_name": "Salaries Expense",
      "balance": "60000.0000"
    }
  ],
  "total_expenses": "72000.0000",
  "net_income": "28000.0000"
}
```

## GET /api/v1/accounting/reports/balance-sheet/

Get balance sheet as of a date.

### Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `as_of` | string (ISO date) | No | Date (defaults to today) |

### Response

```json
{
  "report_type": "balance-sheet",
  "as_of": "2026-12-31",
  "assets": [
    {
      "account_id": "uuid",
      "account_name": "Cash",
      "balance": "50000.0000"
    },
    {
      "account_id": "uuid",
      "account_name": "Accounts Receivable",
      "balance": "15000.0000"
    }
  ],
  "total_assets": "65000.0000",
  "liabilities": [
    {
      "account_id": "uuid",
      "account_name": "Accounts Payable",
      "balance": "15000.0000"
    }
  ],
  "total_liabilities": "15000.0000",
  "equity": [
    {
      "account_id": "uuid",
      "account_name": "Owner's Equity",
      "balance": "22000.0000"
    },
    {
      "account_id": "uuid",
      "account_name": "Retained Earnings",
      "balance": "28000.0000"
    }
  ],
  "total_equity": "50000.0000",
  "total_liabilities_and_equity": "65000.0000"
}
```
