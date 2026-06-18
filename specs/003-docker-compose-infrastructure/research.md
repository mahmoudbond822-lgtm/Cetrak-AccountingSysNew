# Research: Docker Compose Infrastructure

**Phase**: 0 | **Date**: 2026-06-16

## Decisions

### Decision 1: Docker Compose file location

- **Decision**: Keep `docker-compose.yml` in `infra/` directory
- **Rationale**: Already exists there with the project's Dockerfile
- **Alternatives considered**: Moving to project root — rejected because `infra/` is the established convention

### Decision 2: Redis configuration

- **Decision**: Use `redis:7-alpine` with no authentication in dev mode, not exposed to host
- **Rationale**: Matches existing PostgreSQL pattern; no auth needed for local dev; internal Docker network ensures isolation
- **Alternatives considered**: Redis with password — overkill for local dev; Bitnami Redis image — no advantage over official

### Decision 3: Worker (Celery) approach

- **Decision**: Worker is opt-in via Docker Compose profile (`--profile worker`)
- **Rationale**: Per FR-008 — worker is a "later" feature; profiles keep it optional without modifying the main compose file
- **Alternatives considered**: Separate compose file — harder to maintain; auto-start — wastes resources

### Decision 4: Backend Dockerfile changes

- **Decision**: Single Dockerfile with conditional requirements (base.txt + Celery/Redis deps)
- **Rationale**: Worker needs Celery + Redis; main app only needs Redis client; single Dockerfile keeps it simple
- **Alternatives considered**: Separate Dockerfiles for backend vs worker — unnecessary complexity for dev

### Decision 5: Frontend proxy configuration

- **Decision**: Frontend dev server proxies API requests to backend via `vite.config.js`
- **Rationale**: Already the standard Vite setup; avoids CORS issues in development
- **Alternatives considered**: Direct backend URL in frontend — requires CORS headers on every request
