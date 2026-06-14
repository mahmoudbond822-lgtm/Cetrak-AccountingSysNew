# Cetrak ERP — Implementation Plan

> **Status**: Finalized | **Date**: 2026-06-13 | **Author**: OpenCode

---

## Product Overview

Cloud-based SaaS ERP system for small businesses with AI-powered accounting.

### Plans
| Plan | Price | Features |
|------|-------|----------|
| Basic | $10/mo | Accounting Core + Invoices |
| Pro | $25/mo | Everything in Basic + AI Features + Reports |
| Enterprise | $50/mo | All features + Priority support |

### Target Market
- Small businesses (global, initial focus: Egypt)
- Business model: Monthly subscription + 14-day free trial

### Key Differentiator
AI-powered accounting and insights layer.

---

## Engineering Constitution

Established at `.specify/memory/constitution.md` — 8 non-negotiable principles:

| # | Principle | Rule |
|---|-----------|------|
| I | Multi-Tenancy | Every table MUST include `tenant_id`; no query without tenant filter; enforced via middleware |
| II | Accounting Integrity | Journal entries MUST balance (debit = credit); no direct edits to posted entries; fully auditable |
| III | API Rules | RESTful; all endpoints require auth; consistent JSON response format |
| IV | Code Standards | Django + DRF; services layer required; no business logic in views |
| V | AI Safety | AI outputs are suggestions only; every response includes confidence score; user must confirm critical actions |
| VI | Security | JWT auth; bcrypt password hashing; tenant isolation enforced |
| VII | Performance | Heavy tasks via Celery async; optimized queries with indexes |
| VIII | MVP Discipline | No feature outside defined scope; prioritize working system over perfection |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django + Django REST Framework |
| **Frontend** | React |
| **Database** | PostgreSQL (UUID extension) |
| **Async** | Celery + Redis |
| **AI** | Generic gateway (provider TBD — external API) |
| **Infrastructure** | Docker, AWS (EC2 + RDS + S3), GitHub Actions CI/CD |

### Testing Framework
- pytest + DRF `APITestCase`

### Project Structure

```
backend/
├── config/
│   ├── settings/
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/              # BaseModel, Tenant, Membership, middleware
│   ├── accounts/          # Custom User model, JWT, auth views
│   ├── accounting/        # Account, JournalEntry, JournalLine, Ledger, Reports
│   ├── sales/             # Customer, Invoice, Payment
│   ├── purchases/         # Supplier, SupplierInvoice
│   └── ai/                # AI gateway service + endpoints
├── requirements/
├── manage.py
└── pytest.ini

frontend/
├── public/
├── src/
│   ├── components/        # Reusable UI components
│   ├── pages/             # Page-level components
│   ├── services/          # API client
│   ├── hooks/
│   ├── App.jsx
│   └── index.jsx
├── package.json
└── .env

infra/
├── docker-compose.yml
├── Dockerfile
└── .github/workflows/
```

---

## Spec Documents (`/specs/`)

| File | Content |
|------|---------|
| `00-constitution.md` | Engineering constitution (adapt from `.specify/memory/constitution.md`) |
| `01-product.md` | Product specification — plans, multi-tenancy, user roles, auth |
| `02-modules.md` | Module breakdown — Accounting, Sales, Purchases, Reports, Users, AI |
| `03-architecture.md` | System architecture — stack diagram, flow, multi-tenancy design |
| `04-database.md` | Database schema — all tables with fields |
| `05-api.md` | API specification — endpoints, methods, request/response |
| `06-ai.md` | AI specification — categorization, reconciliation, insights, chat |
| `07-jobs.md` | Background jobs — daily, weekly, on-demand |
| `08-security.md` | Security — JWT, bcrypt, tenant isolation, roles |
| `09-deployment.md` | Deployment — AWS services, Docker, CI/CD |
| `10-roadmap.md` | 30-day roadmap — week-by-week breakdown |
| `11-tasks.md` | Execution tasks — all phases with detailed task list |

---

## Execution Order (Feature-by-Feature)

### F1 — Foundation
| What | Backend | Frontend |
|------|---------|----------|
| Django project + Docker + PostgreSQL | ✅ | — |
| BaseEntity model (UUID, tenant_id, timestamps) | ✅ | — |
| Tenant + Membership models | ✅ | — |
| Multi-tenancy middleware (global tenant filtering) | ✅ | — |
| Custom User model + JWT auth | ✅ | — |
| Login / Register APIs | ✅ | Login & Register pages |

### F2 — Accounting Core
| What | Backend | Frontend |
|------|---------|----------|
| Chart of Accounts (hierarchical, parent_id) | ✅ | Tree UI |
| Account types: Asset, Liability, Equity, Revenue, Expense | ✅ | — |
| Journal Entry + Journal Line models | ✅ | JE form |
| Validation: debit == credit (non-negotiable) | ✅ | Error display |
| Posting logic (lock after post, no edits) | ✅ | — |
| Ledger calculation engine | ✅ | Ledger view |
| Reports: Trial Balance, Income Statement, Balance Sheet | ✅ | Report views |

### F3 — Sales
| What | Backend | Frontend |
|------|---------|----------|
| Customer model + CRUD | ✅ | Customer list/form |
| Invoice model with status (draft/sent/paid) | ✅ | Invoice create/list |
| Payment model linked to invoices | ✅ | Payment tracking |
| Auto status updates on payment | ✅ | — |

### F4 — Purchases
| What | Backend | Frontend |
|------|---------|----------|
| Supplier model + CRUD | ✅ | Supplier list/form |
| Supplier Invoice model + payment tracking | ✅ | Supplier invoice UI |

### F5 — AI Module
| What | Backend | Frontend |
|------|---------|----------|
| Generic AI gateway service (interface pattern, provider TBD) | ✅ | — |
| Auto Categorization endpoint | ✅ | Smart suggestion UI |
| Smart Reconciliation endpoint | ✅ | Reconciliation panel |
| Financial Insights endpoint | ✅ | Insights dashboard |
| Chat with ERP endpoint | ✅ | Chat panel |
| All outputs = suggestions + confidence score | ✅ | — |

### F6 — Async Jobs
| What | Backend | Frontend |
|------|---------|----------|
| Celery + Redis setup | ✅ | — |
| Daily: reconciliation, low balance alerts | ✅ | Notification badges |
| Weekly: AI financial insights | ✅ | Insights refresh |
| On-demand: report generation | ✅ | Report download |

### F7 — Deployment
| What | Details |
|------|---------|
| Docker Compose | Local dev environment |
| Dockerfile | Production image |
| AWS EC2 | Backend hosting |
| AWS RDS | PostgreSQL |
| AWS S3 | File storage |
| GitHub Actions | CI/CD pipeline |
| Domain + SSL | HTTPS setup |

### Post-MVP
- Stripe subscription integration
- Paymob local payments (Egypt)

---

## Definition of Done

A feature is complete **only if**:

- [ ] API works (tested with pytest + DRF APITestCase)
- [ ] Tenant-safe (multi-tenancy enforced)
- [ ] UI connected (where applicable)
- [ ] No critical bugs
- [ ] Constitution compliant

---

## Architecture Flow

```
Frontend (React)
    ↓
REST API (Django REST Framework)
    ↓
Services Layer (business logic)
    ↓
Database (PostgreSQL with tenant_id isolation)
    ↓
AI Gateway (external API — provider TBD)
    ↓
Async Workers (Celery + Redis)
```

---

## Roles

| Role | Permissions |
|------|------------|
| Admin | Full access |
| Accountant | Accounting + Sales + Purchases |
| Manager | Reports + Dashboard (read-only) |
