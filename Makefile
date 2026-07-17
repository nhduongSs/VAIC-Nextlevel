.PHONY: help install dev migrate-up migrate-down migrate-create \
        lint format typecheck test test-cov \
        docker-up docker-down docker-logs docker-reset \
        clean

BACKEND_DIR = backend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Local Development ─────────────────────────────────────────────────────────

install: ## Install all dependencies (requires uv)
	cd $(BACKEND_DIR) && pip install uv && uv pip install --system -e ".[dev]"

dev: ## Start backend in hot-reload mode
	cd $(BACKEND_DIR) && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ── Database ──────────────────────────────────────────────────────────────────

migrate-up: ## Apply all pending migrations
	cd $(BACKEND_DIR) && alembic upgrade head

migrate-down: ## Rollback last migration
	cd $(BACKEND_DIR) && alembic downgrade -1

migrate-create: ## Create a new migration (usage: make migrate-create name="add_users_table")
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(name)"

migrate-history: ## Show migration history
	cd $(BACKEND_DIR) && alembic history --verbose

# ── Code Quality ──────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	cd $(BACKEND_DIR) && ruff check .

format: ## Run ruff formatter
	cd $(BACKEND_DIR) && ruff format .

typecheck: ## Run mypy type checker
	cd $(BACKEND_DIR) && mypy .

# ── Tests ─────────────────────────────────────────────────────────────────────

test: ## Run all tests
	cd $(BACKEND_DIR) && pytest

test-cov: ## Run tests with coverage report
	cd $(BACKEND_DIR) && pytest --cov=app --cov-report=html
	@echo "Coverage report: backend/htmlcov/index.html"

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up: ## Start all services
	docker compose up -d

docker-dev: ## Start services in dev mode with hot-reload
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Follow backend logs
	docker compose logs -f backend

docker-reset: ## Full reset (removes volumes — DELETES ALL DATA)
	docker compose down -v

docker-migrate: ## Run migrations inside running backend container
	docker compose exec backend alembic upgrade head

docker-ps: ## Show service status
	docker compose ps

# ── Utility ───────────────────────────────────────────────────────────────────

clean: ## Remove Python caches
	find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	find $(BACKEND_DIR) -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
