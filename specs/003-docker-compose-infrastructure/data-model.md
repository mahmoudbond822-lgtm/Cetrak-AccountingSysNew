# Data Model: Docker Compose Infrastructure

**Phase**: 1 | **Date**: 2026-06-16

No new database entities are introduced by this feature. This document describes the environment variable contracts and service configuration instead.

## Environment Variables

### Backend Service

| Variable | Source | Purpose | Example |
|----------|--------|---------|---------|
| `DJANGO_SETTINGS_MODULE` | docker-compose.yml | Selects Django settings | `config.settings.dev` |
| `POSTGRES_HOST` | docker-compose.yml | DB hostname | `db` |
| `POSTGRES_DB` | docker-compose.yml | DB name | `cetrak` |
| `POSTGRES_USER` | docker-compose.yml | DB user | `cetrak` |
| `POSTGRES_PASSWORD` | docker-compose.yml | DB password | `cetrak` |
| `REDIS_HOST` | docker-compose.yml | Redis hostname | `redis` |
| `REDIS_PORT` | docker-compose.yml | Redis port | `6379` |

### Worker Service

| Variable | Source | Purpose | Example |
|----------|--------|---------|---------|
| `CELERY_BROKER_URL` | docker-compose.yml | Redis broker URL | `redis://redis:6379/0` |
| `DATABASE_URL` | docker-compose.yml | DB connection string | (constructed from PG env vars) |

## Service Contracts

### Service Discovery

| Service | Internal Hostname | Internal Port | Exposed Port |
|---------|------------------|---------------|--------------|
| db | `db` | 5432 | 5432 |
| redis | `redis` | 6379 | (not exposed) |
| backend | `backend` | 8000 | 8000 |
| frontend | `frontend` | 5173 | 5173 |
| worker | `worker` | (no HTTP) | (not exposed) |

### Health Check Endpoints

- **Backend**: `GET /api/v1/health/` — returns 200 when the app is ready
- **Database**: `pg_isready -U cetrak` — checks PostgreSQL readiness
- **Redis**: `redis-cli ping` — checks Redis readiness
