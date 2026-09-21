# Implementation Plan: Auto Journal Entry Code

**Branch**: `014-auto-journal-entry-code` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

## Summary

Creating a journal entry currently fails with "code required" error when no code is entered. This plan makes the system own the code: the backend mints the next per-business code (`JE-YYYY-0001`, +1 per saved journal entry) at save time, and the create form shows that next code in a visible but disabled (non-editable) field. Preview is a hint only — authoritative assignment happens at save, skipping collisions, scoped per business, immutable on edit.

## Technical Context

- **Language/Version**: Python 3.14 backend (Django + DRF); React frontend (existing toolchain, npm)
- **Primary Dependencies**: Django, Django REST Framework (backend); React (frontend)
- **Storage**: SQLite for dev/test (`config.settings.test`); Postgres via Docker Compose for prod-like env
- **Testing**: `py -m pytest apps/ -q` with `DJANGO_SETTINGS_MODULE=config.settings.test`

## Constraints

- Behavior-only change (no migration required)
- Tenant isolation must hold on every query
- No journal/ledger touch; codes immutable on edit, never blanked or regenerated
- Only journal entry creation changes; customer, vendor, account, and invoice numbering behavior is out of scope

## Scale/Scope

One service path (`JournalService` in `backend/apps/journal/services.py`):
- `create()` mints next code and persists
- Code format: `JE-YYYY-0001` (year resets each January 1st)

One serializer path (`JournalEntrySerializer` in `backend/apps/journal/serializers.py`):
- Handles code assignment at save time
- Validates uniqueness per business per year

One frontend component update (`frontend/src/components/journal/JournalEntryForm.jsx`):
- Add disabled preview code field on create
- Ensure code field is non-editable on edit/posted state

## Project Structure

```
specs/014-auto-journal-entry-code/
├── plan.md              # This file
├── research.md           # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── journal-entry-code.md
└── tasks.md             # Phase 2 output
```

### Source Code

```
backend/
├─ apps/journal/
│   ├─ models.py        # JournalEntry (unchanged schema)
│   ├─ serializers.py   # JournalEntrySerializer: code auto-minted
│   ├─ services.py      # JournalService.create + next-code helper
│   ├─ views.py         # Journal view: create with code mint
│   └─ tests/
│       └── test_auto_journal_entry_code.py
```

### Frontend Changes

- `JournalEntryForm.jsx`: Add disabled code preview field
- `JournalPage.jsx`: Handle assigned code display

## Success Metrics

- **SC-001**: 100% success rate for creating journal entries without manual code entry
- **SC-002**: Zero "code required" errors in production
- **SC-003**: No duplicate journal entry codes within a business
- **SC-004**: All edits preserve original code unchanged

## Checklist

- [x] Specification written to `specs/014-auto-journal-entry-code/spec.md`
- [x] Plan documented in `specs/014-auto-journal-entry-code/plan.md`
- [ ] Implementation follows existing patterns (customer/vendor/invoice)
- [ ] Backend mints next code at save time
- [ ] Frontend shows disabled code preview
- [ ] Code immutable on edit (draft and posted)
- [ ] Cross-tenant isolation maintained
- [ ] Lint and test passes