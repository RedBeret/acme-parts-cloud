# AcmeParts Cloud — QUIRKS.md

This file documents every intentional defect in the synthetic dataset.
These quirks mirror what real enterprise systems accumulate over years.
They are the reason this sandbox is useful for integration demos and ETL tutorials.

> **All data is synthetic.** Meridian Fabrication Co. is a fictional company.

---

## Part Numbers

**Three naming eras exist simultaneously:**

| Era | Format | Example | When introduced |
|-----|--------|---------|-----------------|
| Legacy (pre-2015) | `P{N}` (no padding) | `P1`, `P42` | Original system |
| 2019 migration | `2019-PN-{N}` | `2019-PN-1042` | ERP upgrade |
| Current (2021+) | `PN-{N:04d}` | `PN-1042` | Current standard |

**Why it matters for integrations:** a lookup by part number must handle all three formats or miss records. A regex like `^PN-\d+$` silently misses ~12% of the catalog under medium messiness.

---

## Part Revisions

**Mixed revision code schemes:**
Some parts use letter codes (A, B, C…), others use numeric codes (1, 2, 3…). A minority have both — a legacy part that switched schemes mid-life. There is no column indicating which scheme applies; you have to infer it.

**Retroactive effective dates:**
Under medium/chaos messiness, some revision rows have an `effective_date` earlier than the previous revision. This happens in real systems when revisions are backfilled or entered out of order.

---

## Suppliers

**Near-duplicate names:**
The same supplier appears under multiple name variants:
- `Vortex Metals`, `Vortex Metals Inc.`, `VORTEX METALS`

These are the *same* supplier with different data entry. Entity resolution is required before any supplier-level aggregation is meaningful.

**Invalid contact emails:**
Some `contact_email` values are malformed: missing `@`, extra `.invalid` suffix, or just a first name. Percentage depends on `MESSINESS` level.

**Defunct suppliers still referenced in purchase orders:**
~8% of suppliers have `active=false`. They still appear in `purchase_orders` because nobody cleaned up historical records. Joining on `active=true` silently drops historical purchase data.

---

## Change Orders

**State vocabulary inconsistency:**
The `state` column contains values from at least three vocabularies that accumulated as different teams used the system:

| Canonical | Variants found |
|-----------|---------------|
| `open` | `OPEN`, `open` |
| `in-review` | `In-Work`, `in_review`, `in-review` |
| `approved` | `Approved`, `APPROVED`, `approved` |
| `closed` | `CLOSED`, `closed` |
| `rejected` | `REJECTED`, `rejected` |

**Why it matters:** `WHERE state = 'open'` misses `OPEN` and `In-Work` records. Any pipeline that normalizes states must account for all variants.

**Impossible dates:**
Some `closed_at` timestamps precede `opened_at`. This happens in real systems when records are migrated or timestamps are entered manually. Percentage controlled by `MESSINESS`.

---

## Purchase Orders

**Price magnitude errors:**
A small percentage of `unit_price` values are multiplied by `100`, `0.01`, or `1000`. These are not outlier products — they're data entry errors.

**Mixed currencies without conversion:**
`unit_price` is stored in `currency` (USD, EUR, GBP, etc.), but there is no exchange rate table and prices are not normalized. Comparing `SUM(unit_price)` across currencies produces a meaningless number — this is the correct behavior for a real system that accumulated international suppliers without a finance module.

---

## Audit Log

**Missing actors:**
Some audit log rows have `actor = NULL`. These represent automated system actions or records migrated from a system that didn't capture the actor.

## Exports

| File | Defects |
|------|---------|
| `parts_v1.csv` | 2019-era column names (`partNo`, `partName`, `cat`, `measure`) |
| `parts_v2.csv` | Extra null `legacy_ref` column; `uom` column moved before `category` |
| `change_orders.xlsx` | Row 1 is a merged section header (not column names); `Description` column has embedded newlines |
| `suppliers_legacy.csv` | Windows-1252 encoding; will appear garbled if opened as UTF-8 |

The `samples/` directory contains small committed samples of each file so README examples work without running the full export.

---

## Messiness Levels

Control with `MESSINESS=clean|medium|chaos` environment variable.

| Level | Configurable injection effect |
|-------|--------|
| `clean` | Defect injection rates ~2%. Useful for baseline testing. |
| `medium` | Defect injection rates ~10%. Realistic enterprise system. **(default)** |
| `chaos` | Defect injection rates ~25%. Stress-test your cleaning logic. |

These levels control format, duplicate, email, state, date, and price injections. Mixed currencies, inactive records, missing actors, and export-format quirks are structural and remain at fixed rates.

The `mess_manifest.json` file emitted by the seeder records stable affected-row keys under `defect_records` and counts derived from those keys under `defect_counts`. Use manifest v2 as ground truth when building or evaluating cleaning pipelines.
