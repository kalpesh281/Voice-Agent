.PHONY: install run api seed seed-all test lint clean

install:
	poetry install

run:
	poetry run python -m app.main

# Client onboarding API (FastAPI)
api:
	poetry run python -m app.api.server

# Seed MongoDB with client config and resources
seed:
	poetry run python scripts/seed_client.py --all
	poetry run python scripts/seed_resources.py --all

seed-hotel:
	poetry run python scripts/seed_client.py --category hotel
	poetry run python scripts/seed_resources.py --category hotel

seed-restaurant:
	poetry run python scripts/seed_client.py --category restaurant
	poetry run python scripts/seed_resources.py --category restaurant

seed-turf:
	poetry run python scripts/seed_client.py --category cricket_ground
	poetry run python scripts/seed_resources.py --category cricket_ground

# Testing
test:
	poetry run pytest tests/ -v

test-deepgram:
	poetry run python scripts/test_deepgram.py

# Code quality
lint:
	poetry run ruff check app/ tests/ scripts/

lint-fix:
	poetry run ruff check --fix app/ tests/ scripts/

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
