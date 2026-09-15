# Research: Auto Customer Code

**Feature**: `013-auto-customer-code` | **Date**: 2026-09-14

All Technical Context unknowns are resolved — no NEEDS CLARIFICATION remains (spec + clarification session 2026-09-14 cover format, scope, and conflict behavior). Findings below consolidate prior-session evidence from this working tree.

## Decision 1: Mint location — backend at save time (single source of truth)

- **Decision**: The code is minted in `CustomerService` at POST time (`create` / `create_with_flag`); the frontend never computes or submits a code (create payload omits it).
- **Rationale**: One authoritative minter eliminates client/server skew and keeps tenant scoping in the services layer per the constitution. Replay-verified: POST `{"name":"Acme Corp"}` with no code → `201 {"code":"CUS-0001"}`; second create → `CUS-0002`.
- **Alternatives considered**: Frontend-computed preview-as-value (rejected — two dialogs could claim the same code; breaks tenant truth); DB sequence column (rejected — schema migration for a presentation problem; existing CharField + unique constraint suffices).

## Decision 2: Preview is a non-binding hint (clarification 2026-09-14, Option A)

- **Decision**: The create dialog shows the next code disabled, but opening the dialog reserves nothing. At save, the backend assigns the next free code; if the preview was taken concurrently, the save still succeeds with the next free code plus a note showing the assigned code. Cancelled/abandoned dialogs consume nothing.
- **Rationale**: Reservations leak codes on every cancel and need lock/expiry machinery; mint-at-save with collision-skip is simpler and preserves the monotonic no-reuse assumption.
- **Alternatives considered**: Reject-with-retry on stale preview (rejected — punishes the user for a race they didn't cause); lock-on-open (rejected — abandonment gaps + complexity).

## Decision 3: Format `CUS-0001` zero-padded, monotonic, per business

- **Decision**: Per-business prefix `CUS-` + zero-padded 4-digit sequence (`CUS-0001`, `CUS-0002`, …); never reused, gaps from deletions kept; each business has an independent sequence.
- **Rationale**: Taken verbatim from the user request; matches the existing `PUR-INV-{n}` convention style. Service tests assert `CUS-0001`/`CUS-0002` and cross-business independence (each first customer → `CUS-0001`).
- **Alternatives considered**: Non-padded `CUS-1` (rejected — user explicitly wrote `CUS-0001`); global sequence (rejected — violates per-tenant uniqueness model).

## Decision 4: Collision strategy — max-suffix + 1 with skip loop

- **Decision**: Next code = max numeric suffix of the business's existing customer codes + 1; if the candidate exists (race with a manually entered code), increment until free. Bounded loop, same pattern as the document-number handling in prior hardening.
- **Rationale**: Collision-aware without migrations; handles legacy manual codes that squat future values. Explicit duplicate POST in the same business is idempotent (same row, `200`, no new row).
- **Alternatives considered**: Rely on DB unique error → 400 (rejected — turns a predictable race into a user-facing error, contradicting Decision 2).

## Decision 5: Edit path — code immutable and read-only

- **Decision**: Edit never blanks, regenerates, or requires code; the edit dialog shows code read-only (`CustomerModal.jsx:73-77` already does this; payload excludes code).
- **Rationale**: Protects invoice/receipt/ledger references. Service test covers name-change-preserves-code.
- **Alternatives considered**: None — unanimous with spec FR-006.

## Decision 6: No migration, no new endpoint

- **Decision**: Behavior + presentation only. `makemigrations --check --dry-run` stays clean; no new routes — the existing create/list/update contract covers it.
- **Rationale**: Schema already supports everything (CharField + per-tenant unique constraint); full suite green at 375 passed / 1 skipped with this approach.
