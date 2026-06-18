# Contributing to AcmeParts Cloud

Thanks for your interest. This project uses Docker for runtime and a Python venv for local development and testing.

## Prerequisites

- Python 3.12+
- Docker Desktop (for full integration runs)
- Git

## Local Setup

```bash
# Clone
git clone https://github.com/RedBeret/acme-parts-cloud.git
cd acme-parts-cloud

# Create venv
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate.bat     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Running Tests

The unit tests (seed determinism, schema validation) run without Docker:

```bash
pytest tests/test_seed.py -v
```

The smoke tests require a live API. Start with Docker first, then:

```bash
SMOKE_API_URL=http://localhost:8000 pytest tests/test_api_smoke.py -v
```

## Docker Workflow

```bash
# Start everything
docker compose up --build

# Reseed with a different seed value
curl -X POST "http://localhost:8000/admin/reset?seed=99"

# Stop
docker compose down
```

## Linting

```bash
ruff check .
ruff format --check .
```

## Project Layout

```
app/
  api/          FastAPI routers (parts, suppliers, change_orders, admin)
  seed/         Seed engine (generators, manifest writer, exporter)
  ui/
    templates/  Jinja2 HTML templates
  database.py   SQLAlchemy session factory
  main.py       FastAPI app entry point
  models.py     ORM models
tests/
  test_seed.py         Unit tests (no DB required)
  test_api_smoke.py    Smoke tests (requires SMOKE_API_URL)
samples/        Committed small export samples for README examples
```

## Adding a New Quirk

1. Add a defect injection function in `app/seed/generators.py`
2. Respect the `MESS_RATES[MESSINESS]` dict for the injection rate
3. Record the count in the stats dict returned by the generator
4. Update `mess_manifest.json` via `app/seed/manifest.py`
5. Document the quirk in `QUIRKS.md`

## Commit Style

```
feat: add purchase order volume filter
fix: correct cursor pagination off-by-one
docs: update QUIRKS.md with new date defect
```

No Co-Authored-By lines. No AI attribution.
