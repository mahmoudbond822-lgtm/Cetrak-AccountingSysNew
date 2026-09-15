# Contract: Customer Create with Auto Code

**Feature**: `013-auto-customer-code` | **Date**: 2026-09-14

Covers the existing customer endpoints' behavior under this feature. No new routes.

## Create customer (code auto-minted)

- **Request**: `POST /api/v1/sales/customers/` with `{"name": "<name>"}` — no `code` key (blank/whitespace `code` behaves identically).
- **Response 201**: customer object including `"code": "CUS-0001"` (first of business), then `CUS-0002`, … per saved customer.
- **Stale preview rule**: if the previewed code was taken before save, the save still succeeds with the next free code, and the response carries the assigned code (client surfaces it with a note).

## Create with explicit code (legacy/manual path preserved)

- **Request**: `POST /api/v1/sales/customers/` with `{"name": ..., "code": "CUS-0042"}` → respected as-is.
- **Idempotent duplicate**: repeating the same explicit code in the same business returns the existing row (`200`, no new row).

## Edit customer (code immutable)

- **Request**: `PATCH /api/v1/sales/customers/{id}/` with name/contact fields (no `code`).
- **Response 200**: customer with the original `code` unchanged; a submitted code value is ignored, never blanked or regenerated.

## List customers

- **Request**: `GET /api/v1/sales/customers/`
- **Response 200**: list entries each include their `code` (minted or manual).
