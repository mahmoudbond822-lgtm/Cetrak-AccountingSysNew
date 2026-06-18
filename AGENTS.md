<!-- SPECKIT START -->
Implementation plan: specs/005-accounting-schema/plan.md

Quick reference:
- Backend tests: `cd backend && py -m pytest apps/accounts/tests/ -v`
- Accounting tests: `cd backend && py -m pytest apps/accounting/tests/ -v`
- Frontend build: `cd frontend && npx vite build`
- Test settings: DJANGO_SETTINGS_MODULE=config.settings.test
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
- Docker Compose (with worker): `docker compose -f infra/docker-compose.yml --profile worker up`
<!-- SPECKIT END -->
