# Contract: Invoice Create with Auto Number

**Feature**: `016-auto-invoice-number` | **Date**: 2026-09-16

Covers the existing sales and purchase invoice endpoints' behavior under this feature. No new routes. Both sides behave identically except for the URL and the linked party (customer vs vendor).

## Create invoice (number auto-minted)

- **Sales request**: `POST /api/v1/sales/invoices/` with customer, dates, lines — no `number` key (blank/whitespace `number` behaves identically).
- **Purchase request**: `POST /api/v1/purchases/invoices/` with vendor, dates, lines — no `number` key.
- **Response 201**: invoice object including `"number": "INV-0001"` (first of that type in the business), then `INV-0002`, … per saved invoice of that type.
- **Stale preview rule**: if the previewed number was taken before save, the save still succeeds with the next free number of that type, and the response carries the assigned number (client surfaces it with a note).

## Create with explicit number (manual path preserved)

- **Request**: same endpoints with `"number": "INV-0042"` → respected as-is.
- **Duplicate**: repeating an existing number of the same type in the same business is rejected (`400 "Invoice number already exists"`), unchanged from today. No idempotent-merge behavior.

## Edit invoice (number locked)

- **Request**: `PATCH /api/v1/sales/invoices/{id}/` (or purchases equivalent) with dates/lines/party fields (no `number`; a submitted `number` is ignored).
- **Response 200**: invoice with the original `number` unchanged, in both draft and posted-editable respects (only drafts are editable at all, as today).

## List invoices

- **Request**: `GET /api/v1/sales/invoices/` / `GET /api/v1/purchases/invoices/`
- **Response 200**: list entries each include their `number` (minted or manual).
