.PHONY: db api test

db:
	docker compose up -d

api:
	.venv/bin/uvicorn app.main:app --reload --port 8000 --app-dir backend

test:
	.venv/bin/pytest -q backend/tests
