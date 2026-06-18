.PHONY: up down seed export test reset lint

up:
	docker compose up --build

down:
	docker compose down -v

seed:
	docker compose exec api python -m app.seed.run

export:
	docker compose exec api python -m app.seed.exporter
	@echo "Exports written to exports/"

test:
	pytest tests/ -v

reset:
	docker compose exec api python -m app.seed.run --reset

lint:
	ruff check app/ tests/
