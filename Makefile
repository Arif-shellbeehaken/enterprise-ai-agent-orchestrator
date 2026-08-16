.PHONY: help install test lint backend frontend docker-up docker-down ci migrate

help:
	@echo "Enterprise AI Agent Orchestrator"
	@echo ""
	@echo "  make install     Install backend + frontend deps"
	@echo "  make test        Run backend pytest suite"
	@echo "  make lint        Ruff check backend"
	@echo "  make backend     Run API (uvicorn reload)"
	@echo "  make frontend    Run Next.js dev server"
	@echo "  make docker-up   Start Postgres + backend via Compose"
	@echo "  make docker-down Stop Compose stack"
	@echo "  make ci          Local CI approximation (test + frontend build)"

install:
	cd backend && python -m pip install -r requirements.txt
	cd frontend && npm install

test:
	cd backend && PYTHONPATH=. pytest tests/ -v --tb=short

lint:
	cd backend && pip install -q ruff && ruff check app tests

backend:
	cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

ci: test
	cd frontend && npm install --no-fund --no-audit && NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build
