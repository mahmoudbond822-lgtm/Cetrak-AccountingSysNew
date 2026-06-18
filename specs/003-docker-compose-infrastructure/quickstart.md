# Quickstart: Docker Compose Infrastructure

**Phase**: 1 | **Date**: 2026-06-16

## Prerequisites

- Docker Engine 24+ with Docker Compose V2

## Quick Start

```bash
# From the repository root:
docker compose -f infra/docker-compose.yml up
```

This starts: backend, frontend, PostgreSQL, and Redis.

Wait for all services to become healthy, then:
- **Backend API**: http://localhost:8000
- **Frontend UI**: http://localhost:5173
- **Health check**: http://localhost:8000/api/v1/health/

## Validation Scenarios

### Scenario 1: Full stack starts

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps
```

Expected: all 4 services (db, redis, backend, frontend) show "running" or "healthy".

### Scenario 2: Backend health check

```bash
curl http://localhost:8000/api/v1/health/
```

Expected: HTTP 200 with JSON response.

### Scenario 3: Frontend loads

Open http://localhost:5173 in a browser.

Expected: Application UI loads without console errors.

### Scenario 4: Database persistence

```bash
# Create data, then:
docker compose -f infra/docker-compose.yml down
docker compose -f infra/docker-compose.yml up -d
```

Expected: Previously created data is still accessible.

### Scenario 5: Redis connectivity

The backend health endpoint or Django shell can verify Redis connectivity via the `REDIS_HOST` / `REDIS_PORT` environment variables.

### Scenario 6: Worker (opt-in)

```bash
docker compose -f infra/docker-compose.yml --profile worker up -d
```

Expected: A `worker` service appears in the service list alongside the other services.

## Stopping

```bash
# Stop all services (preserves data):
docker compose -f infra/docker-compose.yml down

# Stop all services and delete volumes (removes all data):
docker compose -f infra/docker-compose.yml down -v
```

## Reference

- Data model and env vars: [data-model.md](./data-model.md)
- Service contracts: [contracts/service-contracts.md](./contracts/service-contracts.md)
