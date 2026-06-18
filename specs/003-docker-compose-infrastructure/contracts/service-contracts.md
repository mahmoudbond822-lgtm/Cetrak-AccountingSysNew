# Service Contracts: Docker Compose Infrastructure

**Phase**: 1 | **Date**: 2026-06-16

This document defines the inter-service communication contracts for the Docker Compose development stack.

## Network

All services reside on the default Docker Compose network (`003-docker-compose-infrastructure_default`). Services discover each other by their service name (hostname).

## Backend Service Contract

**Service name**: `backend`
**Internal port**: 8000
**Exposed port**: 8000

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health/` | GET | Health check |

**Expected environment variables**:
- `DJANGO_SETTINGS_MODULE` = `config.settings.dev`
- `POSTGRES_HOST` = `db`
- `POSTGRES_DB` = `cetrak`
- `POSTGRES_USER` = `cetrak`
- `POSTGRES_PASSWORD` = `cetrak`
- `REDIS_HOST` = `redis`
- `REDIS_PORT` = `6379`

## Frontend Service Contract

**Service name**: `frontend`
**Internal port**: 5173
**Exposed port**: 5173 (mapped from 3000 on earlier setup)

**Expected behavior**: Hot-reload on source file changes via Vite dev server.

**API proxy**: The Vite dev server proxies `/api/*` requests to `http://backend:8000`.

## Database Service Contract

**Service name**: `db`
**Internal port**: 5432
**Exposed port**: 5432

**Connection parameters**:
- Database: `cetrak`
- User: `cetrak`
- Password: `cetrak`

**Initialization**: `init-db.sql` runs on first start to enable `uuid-ossp` extension.

**Health check**: `pg_isready -U cetrak`

## Redis Service Contract

**Service name**: `redis`
**Internal port**: 6379
**Exposed port**: (not exposed to host)

**Connection**: `redis://redis:6379/0`
**Authentication**: None (development only)

**Health check**: `redis-cli ping` (expects `PONG` response)

## Worker Service Contract (Opt-in)

**Service name**: `worker`
**Profile**: `worker` (start with `docker compose --profile worker up`)

**Expected environment variables**:
- `CELERY_BROKER_URL` = `redis://redis:6379/0`
- All backend database env vars

**Behavior**: Connects to Redis as message broker and database for task results. Processes tasks from Celery queues.
