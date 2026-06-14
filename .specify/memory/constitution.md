<!--
  Sync Impact Report:
  - Version change: N/A (initial constitution) → v1.0.0
  - Modified principles: None (initial creation)
  - Added sections: Multi-Tenancy, Accounting Integrity, API Rules, Code Standards,
    AI Safety Rules, Security, Performance, MVP Discipline, Governance
  - Removed sections: None
  - Templates requiring updates: None (all templates are generic, no principle-specific refs)
  - Follow-up TODOs: None
-->

# Cetrak Accounting System Constitution

## Core Principles

### I. Multi-Tenancy (NON-NEGOTIABLE)
Every table MUST include a `tenant_id` column. No query is allowed without tenant
filtering. Tenant data isolation MUST be enforced via middleware at the application
layer.

### II. Accounting Integrity (CRITICAL)
Journal entries MUST always balance (debit = credit). No direct edits to posted
entries are permitted. All financial operations MUST be auditable with a complete,
immutable audit trail.

### III. API Rules
All endpoints MUST be RESTful. Every endpoint MUST require authentication. Responses
MUST follow a consistent JSON format with standardized error structures.

### IV. Code Standards
Backend MUST use Django + DRF. A dedicated services layer is required — no fat
views. Business logic MUST NOT reside in controllers/views; it belongs exclusively
in the services layer.

### V. AI Safety Rules
AI outputs are suggestions, not auto-applied. Every AI-generated response MUST
include a confidence score. Users MUST explicitly confirm any critical actions
before execution.

## Security & Performance Standards

### VI. Security
JWT authentication is required for all endpoints. Passwords MUST be hashed with
bcrypt. Tenant data isolation MUST be enforced at both the database and application
levels.

### VII. Performance
All heavyweight tasks MUST be async (Celery). Database queries MUST be optimized
with appropriate indexes on all JOIN, WHERE, and ORDER BY columns.

## MVP Discipline

### VIII. MVP Discipline
No feature outside the defined project scope is permitted. Prioritize delivering
a working system over perfection. Each iteration MUST deliver incremental,
independently testable value.

## Governance

This constitution supersedes all other development practices. Amendments require:
- Documentation of the proposed change
- Approval from the project lead or designated reviewer
- A migration plan for existing code or processes

All PRs and reviews MUST verify compliance with this constitution. Any deviation
from non-negotiable principles MUST be explicitly justified in the Complexity
Tracking section of implementation plans.

**Version**: 1.0.0 | **Ratified**: 2026-06-13 | **Last Amended**: 2026-06-13
