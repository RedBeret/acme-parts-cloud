# AcmeParts Cloud

[![CI](https://github.com/RedBeret/acme-parts-cloud/actions/workflows/ci.yml/badge.svg)](https://github.com/RedBeret/acme-parts-cloud/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

> **All data is synthetic.** Meridian Fabrication Co. is a fictional company created for integration demonstrations. No real companies, part numbers, or employees are represented.

A self-contained FastAPI + PostgreSQL sandbox that ships 5,000+ parts, 400 suppliers, 20,000 change orders, and 30,000 purchase orders, all seeded with **deterministic, configurable messiness**.

Built for engineers who need a realistic target system to build and demo data pipelines, ETL connectors, or AI-assisted data cleaning without touching production.

---

## What's Inside

| Entity | Rows (medium messiness) | Key quirks |
|--------|------------------------|------------|
| Parts | 5,000 | Three part-number formats from three eras |
| Part Revisions | ~12,000 | Mixed revision schemes (A/B/C vs 1/2/3) |
| Suppliers | 400 | Near-duplicate names, invalid emails |
| Change Orders | 20,000 | 5 state vocabulary variants, impossible dates |
| Purchase Orders | 30,000 | Mixed currencies, price magnitude errors |
| Users | 150 | Inactive users still referenced in COs |
| Audit Log | auto | Missing actors, clock skew |

See [QUIRKS.md](QUIRKS.md) for the full defect catalog.

---

## Architecture

```mermaid
graph TD
    Browser["Browser / API Client"] --> API["FastAPI :8000"]
    API --> DB["PostgreSQL 16"]
    API --> Seed["Seed Engine"]
    Seed --> Gen["generators.py<br>5K parts · 400 suppliers<br>20K COs · 30K POs"]
    Seed --> Manifest["mess_manifest.json<br>(ground truth)"]
    Seed --> Exporter["exporter.py<br>CSV · XLSX · legacy encodings"]
    API --> UI["Jinja2 + HTMX<br>Dashboard · Parts · Suppliers · COs"]
```

---

## Quick Start

### SQLite — no Docker, no Postgres (quickest)

Point `DATABASE_URL` at SQLite and scale the row counts down so a laptop seeds in seconds:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="sqlite:///acme.db"
export PARTS_COUNT=500 CHANGE_ORDERS_COUNT=2000 PURCHASE_ORDERS_COUNT=3000 AUDIT_LOG_COUNT=5000

python -m app.seed.run
uvicorn app.main:app --reload
```

Open http://localhost:8000/. Drop the count overrides to seed the full-size dataset (slower on SQLite).

### Docker + Postgres (full dataset)

```bash
git clone https://github.com/RedBeret/acme-parts-cloud.git
cd acme-parts-cloud
docker compose up --build
```

Open http://localhost:8000/; the seeder runs automatically on first boot. On Windows, `run.bat` does the venv setup for you.

### Local venv against your own Postgres

```bash
export DATABASE_URL=postgresql+psycopg2://acme:acme@localhost:5432/acmeparts
export SEED=42
export MESSINESS=medium  # clean | medium | chaos
python -m app.seed.run
uvicorn app.main:app --reload
```

---

## Messiness Levels

Control defect injection with the `MESSINESS` environment variable:

| Level | Defect rate | Use case |
|-------|-------------|----------|
| `clean` | ~2% | Baseline; test happy-path pipelines |
| `medium` | ~10% | Default; realistic enterprise system |
| `chaos` | ~25% | Stress-test your cleaning and dedup logic |

The seeder writes `mess_manifest.json` after each run — a machine-readable ground-truth file recording exactly which defects were injected and at what counts.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/parts` | GET | List/search parts (`q`, `status`, `category`, `after`) |
| `/parts/{id}` | GET | Single part with revisions |
| `/suppliers` | GET | List/search suppliers (`q`, `active`, `after`) |
| `/change-orders` | GET | List COs (`q`, `state`, `priority`, `after`) |
| `/admin/healthz` | GET | Liveness check |
| `/admin/reset` | POST | Reseed with `?seed=N` |
| `/docs` | GET | Interactive Swagger UI |

All list endpoints use **cursor pagination** via the `after` parameter (last seen id).

---

## Sample Exports

The `samples/` directory contains small committed samples of each export format:

```
samples/
  parts_v1_sample.csv         — 2019-era column names
  parts_v2_sample.csv         — schema drift (extra legacy_ref column)
  change_orders_sample.xlsx   — merged header row, embedded newlines
  suppliers_legacy_sample.csv — Windows-1252 encoding
```

Full exports are available at runtime:

```bash
curl http://localhost:8000/exports/parts/v1  > parts_v1.csv
curl http://localhost:8000/exports/parts/v2  > parts_v2.csv
curl http://localhost:8000/exports/suppliers/legacy > suppliers_legacy.csv
curl http://localhost:8000/exports/change-orders > change_orders.xlsx
```

---

## Case Study — Data Cleaning Pipeline Demo

**Scenario:** An engineer is building a Snowflake connector to ingest AcmeParts supplier data for procurement analytics. The pipeline breaks on first run.

**Root cause chain discovered using this sandbox:**

1. `SELECT * FROM suppliers WHERE active = true` — silently drops 8% of historical PO data because defunct suppliers are still referenced in `purchase_orders`.
2. `GROUP BY supplier_name` — returns 3 rows for "Vortex Metals" because of near-duplicate name variants (`Vortex Metals`, `Vortex Metals Inc.`, `VORTEX METALS`). Entity resolution required before aggregation.
3. `SUM(unit_price)` across POs — produces a meaningless number because `unit_price` is in mixed currencies (USD, EUR, GBP) with no exchange rate table.
4. Opening `suppliers_legacy.csv` as UTF-8 — garbled output because the file is Windows-1252 encoded.

Every one of those defects is recorded in `mess_manifest.json` when the data is seeded, so you can check what your pipeline caught against ground truth instead of guessing. That is the whole point of the sandbox: the bugs are known, counted, and reproducible from a seed.

---

## Reseed on Demand

```bash
# Via API
curl -X POST "http://localhost:8000/admin/reset?seed=99"

# Via CLI (inside container)
docker compose exec api python -m app.seed.run --reset
```

Same `SEED + MESSINESS` always produces byte-identical manifest output, and the optional count environment variables let you scale the dataset down for quick CI runs or up for heavier demos.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
