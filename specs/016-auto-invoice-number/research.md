# Research: Auto Invoice Number

**Feature**: `016-auto-invoice-number` | **Date**: 2026-09-16

All Technical Context unknowns are resolved — no NEEDS CLARIFICATION remains (spec + specify-time answers cover scope/format/lifecycle; clarify session 2026-09-16 covers per-type sequences). Findings below adapt the 014/015 evidence to the invoice domain in this working tree.

## Decision 1: Mint location — backend at save time, per-type helpers in existing services

- **Decision**: Each invoice service gains a `next_number()` helper (tenant-scoped `INV-` suffix scan with collision-skip); `create_draft` mints when the number is blank/None. No new service classes — `SalesInvoiceService` and `PurchaseInvoiceService` already own their create paths per the constitution.
- **Rationale**: One authoritative minter per type eliminates client/server skew and keeps tenant scoping in the services layer. Reuses the proven customer/vendor mint loop; per-type helpers avoid cross-app coupling.
- **Alternatives considered**: Shared cross-type minter (rejected in clarify — couples sales+purchases and fights the per-table uniqueness model); frontend-computed preview-as-value (rejected — races); DB sequence column (rejected — migration for a presentation problem).

## Decision 2: Preview is a non-binding hint (same as 014/015)

- **Decision**: Both create dialogs show the next number disabled but reserve nothing. At save, the backend assigns the next free number of that type; a concurrently taken preview still saves successfully with the next free number plus a note. Cancelled dialogs consume nothing. Both list pages gain the `nextNumber` helper + notice pattern.
- **Rationale**: Reservations leak numbers on cancel and need lock/expiry machinery; mint-at-save with collision-skip preserves monotonic no-reuse. Proven in 014/015.
- **Alternatives considered**: Reject-with-retry on stale preview (rejected — punishes the user for a race they didn't cause).

## Decision 3: Format `INV-0001` zero-padded, monotonic, per business per type (specify 2026-09-16)

- **Decision**: Prefix `INV-` + zero-padded 4-digit sequence; sales and purchase run independent sequences (`INV-0001`… each); never reused; gaps from deleted drafts kept; each business independent. Legacy numbers in other formats untouched.
- **Rationale**: Direct mirror of `CUS-`/`VEN-`, confirmed by the user. The same number may exist once as a sale and once as a purchase — harmless, since they are different tables and journal references are type-namespaced.
- **Alternatives considered**: Per-type prefixes (`SI-`/`PI-`, rejected by user); shared interleaved sequence (rejected in clarify — cross-app coupling, fights per-table constraints); global sequence (rejected — violates tenancy model).

## Decision 4: Collision strategy — max-suffix + 1 with skip loop; explicit duplicates rejected

- **Decision**: Next number = max numeric `INV-` suffix of the business's invoices of that type + 1; taken candidates increment until free. An explicit number duplicating an existing invoice of the same type keeps today's rejection (`400 "Invoice number already exists"`) — deliberately different from the customer/vendor idempotent path.
- **Rationale**: Collision-aware without migrations; handles legacy manual numbers squatting future values. Invoices must never silently merge (idempotent return would attach lines to the wrong document), so reject-preserving is the safe choice and keeps existing duplicate tests green.
- **Alternatives considered**: Idempotent 200 on duplicate like customer/vendor (rejected — invoice lines/dates differ per attempt; merging would corrupt documents).

## Decision 5: Edit path — number locked after creation, draft and posted (specify 2026-09-16)

- **Decision**: `update_draft` ignores any submitted number (the `number=None` kwarg stops being applied); both edit dialogs show the number read-only. Drafts remain editable in every other respect.
- **Rationale**: User-confirmed mirror of the code rule; protects journal references derived at posting. Existing draft-edit tests (lines/dates) are unaffected since they don't depend on renumbering.
- **Alternatives considered**: Editable-while-draft (rejected by user); renumber-on-post (rejected — breaks the preview promise and audit trail).

## Decision 6: No migration, no new endpoint; existing explicit-number tests unaffected

- **Decision**: Behavior + presentation only. `makemigrations --check --dry-run` stays clean; no new routes. All existing invoice tests pass explicit numbers, so they exercise the honored-explicit path unchanged.
- **Rationale**: Schema already supports everything (CharField + per-tenant unique constraints per table). New coverage goes in per-app `test_auto_invoice_number.py` modules.
