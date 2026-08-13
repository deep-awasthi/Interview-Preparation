.PHONY: help install dev test lint format check docker-up docker-down docs migrate migrations

help:
	@echo "Aether Object Storage Server Management"
	@echo "--------------------------------------"
	@echo "make install       Install dependencies"
	@echo "make dev           Run development server"
	@echo "make test          Run pytest suite"
	@echo "make lint          Run linters (ruff, black, isort, mypy)"
	@echo "make format        Run code formatters"
	@echo "make docker-up     Start all docker compose services"
	@echo "make docker-down   Stop docker compose services"
	@echo "make docs          Build and serve documentation"

install:
	pip install -r requirements-dev.txt

dev:
	python manage.py runserver 0.0.0.0:8000

test:
	pytest tests/ -v

lint:
	ruff check .
	black --check .
	isort --check .
	mypy aether

format:
	black .
	isort .
	ruff check --fix .

docker-up:
	docker compose -f docker/docker-compose.yml up --build -d

docker-down:
	docker compose -f docker/docker-compose.yml down -v

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

docs:
	mkdocs serve -f docs/mkdocs.yml
