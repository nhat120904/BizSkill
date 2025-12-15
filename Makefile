.PHONY: help build up down logs shell migrate seed test clean

# Default target
help:
	@echo "BizSkill AI - Available commands:"
	@echo ""
	@echo "  make build      - Build all Docker containers"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View service logs"
	@echo "  make shell      - Open shell in backend container"
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed database with initial data"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Remove all containers and volumes"
	@echo ""

# Build containers
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Start with logs
up-logs:
	docker-compose up

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# View specific service logs
logs-backend:
	docker-compose logs -f backend

logs-worker:
	docker-compose logs -f celery-worker

logs-frontend:
	docker-compose logs -f frontend

# Open shell in backend
shell:
	docker-compose exec backend bash

# Open Python shell
shell-python:
	docker-compose exec backend python

# Run database migrations
migrate:
	docker-compose exec backend alembic upgrade head

# Create new migration
migration:
	@read -p "Migration message: " msg; \
	docker-compose exec backend alembic revision --autogenerate -m "$$msg"

# Seed database
seed:
	docker-compose exec backend python /app/scripts/seed.py

# Run backend tests
test:
	docker-compose exec backend pytest

# Run frontend tests
test-frontend:
	docker-compose exec frontend npm test

# Format code
format:
	docker-compose exec backend black app/
	docker-compose exec backend isort app/

# Lint code
lint:
	docker-compose exec backend flake8 app/
	docker-compose exec backend mypy app/

# Clean everything
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Rebuild and restart
rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# Check service status
status:
	docker-compose ps

# Monitor Celery tasks
flower:
	@echo "Opening Flower dashboard..."
	@open http://localhost:5555 || xdg-open http://localhost:5555

# Open API docs
docs:
	@echo "Opening API documentation..."
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs

# Open frontend
web:
	@echo "Opening web application..."
	@open http://localhost:3000 || xdg-open http://localhost:3000

# Development setup
dev-setup:
	cp .env.example .env
	@echo "Please edit .env with your API keys, then run: make build && make up"

# Production build
prod-build:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Backup database
backup:
	docker-compose exec postgres pg_dump -U bizskill bizskill > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Database backed up"

# Restore database
restore:
	@read -p "Backup file: " file; \
	cat $$file | docker-compose exec -T postgres psql -U bizskill bizskill
