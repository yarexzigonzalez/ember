.PHONY: db migrate api web test lint health

db:
	docker compose up -d

migrate:
	cd backend && ../.venv/bin/alembic upgrade head

api:
	.venv/bin/uvicorn app.main:app --reload --port 8000 --app-dir backend

web:
	cd frontend && npm run dev

test:
	cd backend && ../.venv/bin/pytest -q

lint:
	cd backend && ../.venv/bin/ruff check .
	cd frontend && npm run lint && npm run typecheck

health:
	curl -s localhost:8000/api/health
