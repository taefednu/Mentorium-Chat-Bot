.PHONY: help install dev test lint format clean docker-build docker-up docker-down docker-logs migrate validate

help: ## Show this help message
	@echo "Mentorium Chat Bot - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install

dev: ## Run bot in development mode
	cd apps/telegram_bot && poetry run python -m mentorium_bot.main

test: ## Run tests
	poetry run pytest tests/ -v

lint: ## Run linters
	poetry run ruff check .
	poetry run mypy .

format: ## Format code
	poetry run black .
	poetry run ruff check --fix .

clean: ## Clean cache and temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

validate: ## Validate environment variables
	python scripts/validate_env.py

migrate: ## Run database migrations
	cd packages/db && poetry run alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	cd packages/db && poetry run alembic revision --autogenerate -m "$(MSG)"

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all services
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## Show logs from all services
	docker-compose logs -f

docker-logs-bot: ## Show logs from bot service
	docker-compose logs -f bot

docker-logs-webhook: ## Show logs from webhook service
	docker-compose logs -f webhook

docker-restart: ## Restart all services
	docker-compose restart

docker-ps: ## Show running containers
	docker-compose ps

docker-clean: ## Remove all containers, volumes and images
	docker-compose down -v --rmi all

health: ## Check health of services
	@echo "Checking bot health..."
	@curl -f http://localhost:8001/health || echo "❌ Health check failed"
	@echo "\nChecking readiness..."
	@curl -f http://localhost:8001/health/ready || echo "❌ Readiness check failed"
	@echo "\nChecking liveness..."
	@curl -f http://localhost:8001/health/live || echo "❌ Liveness check failed"

metrics: ## Show Prometheus metrics
	curl http://localhost:8001/metrics

backup-db: ## Backup PostgreSQL database
	docker exec mentorium-postgres pg_dump -U mentoriumbot mentorium_bot > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created: backup_$$(date +%Y%m%d_%H%M%S).sql"

restore-db: ## Restore PostgreSQL database (usage: make restore-db FILE=backup.sql)
	@test -n "$(FILE)" || (echo "❌ FILE parameter required. Usage: make restore-db FILE=backup.sql" && exit 1)
	cat $(FILE) | docker exec -i mentorium-postgres psql -U mentoriumbot mentorium_bot
	@echo "✅ Database restored from $(FILE)"

shell-bot: ## Open shell in bot container
	docker-compose exec bot /bin/bash

shell-db: ## Open psql shell in database
	docker-compose exec postgres psql -U mentoriumbot -d mentorium_bot

deploy: validate docker-build docker-up ## Deploy to production (validate + build + up)
	@echo "✅ Deployment complete!"
	@make health

update: ## Update and restart services
	git pull
	docker-compose pull
	docker-compose up -d
	@echo "✅ Services updated!"
