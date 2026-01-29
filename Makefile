.PHONY: help install dev start stop logs status clean build test

help:
	@echo "Homelab Dashboard Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start development servers"
	@echo "  make dev-backend - Start backend only (with reload)"
	@echo "  make dev-frontend- Start frontend only"
	@echo ""
	@echo "Docker:"
	@echo "  make build       - Build Docker images"
	@echo "  make start       - Start all services"
	@echo "  make stop        - Stop all services"
	@echo "  make logs        - View logs"
	@echo "  make status      - Check service status"
	@echo ""
	@echo "Other:"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make test        - Run tests"

# Development
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev: dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload

dev-frontend:
	cd frontend && npm run dev

# Docker
build:
	docker compose build

start:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f

status:
	@echo "=== Docker Status ==="
	@docker compose ps
	@echo ""
	@echo "=== Backend Health ==="
	@curl -s http://localhost:8080/healthz 2>/dev/null | python3 -m json.tool || echo "Backend not running"
	@echo ""
	@echo "=== Services ==="
	@curl -s http://localhost:8080/api/v1/services 2>/dev/null | python3 -m json.tool || echo "API not available"

# Cleanup
clean:
	rm -rf backend/__pycache__ backend/src/__pycache__
	rm -rf frontend/node_modules frontend/dist
	docker compose down -v --rmi local 2>/dev/null || true

# Testing
test:
	cd backend && pytest -v
	cd frontend && npm run lint
