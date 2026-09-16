# Research: Auto Vendor Code

**Feature**: `015-auto-vendor-code` | **Date**: 2026-09-16

All Technical Context unknowns are resolved — no NEEDS CLARIFICATION remains (spec + clarification session 2026-09-16 cover format `VEN-0001`, scope, and conflict behavior). Findings below adapt the Feature 014 evidence to the purchases side of this working tree.

## Decision 1: Mint location — backend at save time in a new `VendorService`

- **Decision**: The code is minted in a new `VendorService` in `apps/purchases/services.py` at POST time (`create_with_flag`, mirroring `CustomerService`); the frontend never computes or submits a code (create payload omits it).
- **Rationale**: One authoritative minter eliminates client/server skew and keeps tenant scoping in the services layer per the constitution. Unlike the customer side, vendor creation currently lives inline in `VendorViewSet.create` (`models.Vendor.objects.get_or_create`), so the service is introduced here to satisfy principle IV (no fat views) rather than reusing view logic.
- **Alternatives considered**: Mint inline in the view (rejected — perpetuates the fat-view violation and splits the mint pattern across two apps); frontend-computed preview-as-value (rejected — two dialogs could claim the same code); DB sequence column (rejected — schema migration for a presentation problem; existing CharField + unique constraint suffices).

## Decision 2: Preview is a non-binding hint (same as 014)

- **Decision**: The create dialog shows the next code disabled, but opening the dialog reserves nothing. At save, the backend assigns the next free code; if the preview was taken concurrently, the save still succeeds with the next free code plus a note showing the assigned code. Cancelled/abandoned dialogs consume nothing. `VendorsPage` gains the same `nextVendorCode` helper + notice pattern `CustomersPage` uses.
- **Rationale**: Reservations leak codes on every cancel and need lock/expiry machinery; mint-at-save with collision-skip is simpler and preserves the monotonic no-reuse assumption. Proven in 014.
- **Alternatives considered**: Reject-with-retry on stale preview (rejected — punishes the user for a race they didn't cause); lock-on-open (rejected — abandonment gaps + complexity).

## Decision 3: Format `VEN-0001` zero-padded, monotonic, per business (clarification 2026-09-16)

- **Decision**: Per-business prefix `VEN-` + zero-padded 4-digit sequence (`VEN-0001`, `VEN-0002`, …); never reused, gaps from deletions kept; each business has an independent sequence. Legacy codes in other formats (e.g., `V-001` seen in existing tests) are never migrated or altered.
- **Rationale**: Direct mirror of the customer `CUS-0001` decision, confirmed by the user in clarification. Legacy `V-001`-style rows coexist untouched; only newly created vendors without a code enter the `VEN-` sequence.
- **Alternatives considered**: `V-0001` matching legacy style (rejected by user — risks visual collision/confusion with manually created codes); global sequence (rejected — violates per-tenant uniqueness model).

## Decision 4: Collision strategy — max-suffix + 1 with skip loop, explicit codes idempotent

- **Decision**: Next code = max numeric suffix of the business's existing vendor codes + 1; if the candidate exists (race with a manually entered code), increment until free. Explicit duplicate POST in the same business stays idempotent (same row, `200`, no new row) — current view behavior preserved inside the service.
- **Rationale**: Collision-aware without migrations; handles legacy manual codes that squat future values. Existing test `test_duplicate_code_same_tenant_idempotent` keeps passing unchanged.
- **Alternatives considered**: Rely on DB unique error → 400 (rejected — turns a predictable race into a user-facing error, contradicting Decision 2).

## Decision 5: Edit path — code immutable and read-only

- **Decision**: Edit never blanks, regenerates, or requires code; the edit dialog shows code read-only and the update payload excludes code, mirroring `CustomerModal` edit mode.
- **Rationale**: Protects purchase-invoice references. `VendorViewSet.partial_update` already rejects duplicate codes; the dialog change removes the ability to attempt it.
- **Alternatives considered**: None — unanimous with spec FR-006.

## Decision 6: No migration, no new endpoint; existing 400-test unaffected

- **Decision**: Behavior + presentation only. `makemigrations --check --dry-run` stays clean; no new routes. `test_create_vendor_requires_code_and_name` posts `{"tax_id": "X"}` with no name — it still returns 400 after the change because `name` remains required, so no existing test needs editing.
- **Rationale**: Schema already supports everything (CharField + per-tenant unique constraint). New coverage goes in a dedicated `test_auto_vendor_code.py` mirroring `test_auto_customer_code.py`.
