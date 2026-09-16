# Contract: Vendor Create with Auto Code

**Feature**: `015-auto-vendor-code` | **Date**: 2026-09-16

Covers the existing vendor endpoints' behavior under this feature. No new routes.

## Create vendor (code auto-minted)

- **Request**: `POST /api/v1/purchases/vendors/` with `{"name": "<name>"}` — no `code` key (blank/whitespace `code` behaves identically).
- **Response 201**: vendor object including `"code": "VEN-0001"` (first of business), then `VEN-0002`, … per saved vendor.
- **Stale preview rule**: if the previewed code was taken before save, the save still succeeds with the next free code, and the response carries the assigned code (client surfaces it with a note).

## Create with explicit code (legacy/manual path preserved)

- **Request**: `POST /api/v1/purchases/vendors/` with `{"name": ..., "code": "VEN-0042"}` → respected as-is.
- **Idempotent duplicate**: repeating the same explicit code in the same business returns the existing row (`200`, no new row).

## Edit vendor (code immutable)

- **Request**: `PATCH /api/v1/purchases/vendors/{id}/` with name/contact fields (no `code`).
- **Response 200**: vendor with the original `code` unchanged; a submitted code value is ignored, never blanked or regenerated.

## List vendors

- **Request**: `GET /api/v1/purchases/vendors/`
- **Response 200**: list entries each include their `code` (minted or manual).
