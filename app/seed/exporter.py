"""Messy export generator.

Produces the four intentionally defective export files documented in QUIRKS.md:
  - parts_v1.csv       (2019-era schema, older column names)
  - parts_v2.csv       (current schema, drifted columns)
  - change_orders.xlsx (merged header rows, embedded newlines in notes column)
  - suppliers_legacy.csv (Windows-1252 encoded)

Run: python -m app.seed.exporter
All data is synthetic.
"""

import csv
import os
from pathlib import Path

from sqlalchemy import text

from app.database import SessionLocal

OUT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))
SAMPLES_DIR = Path("samples")


def export_parts_v1(db) -> None:
    """2019-era schema with old column names (partNo, partName, cat, measure)."""
    rows = db.execute(
        text("SELECT part_number, name, category, uom, status FROM parts LIMIT 2000")
    ).fetchall()
    out = OUT_DIR / "parts_v1.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["partNo", "partName", "cat", "measure", "partStatus"])
        for r in rows:
            writer.writerow(list(r))
    print(f"[export] {out} ({len(rows)} rows)")

    # Committed sample (first 50 rows)
    sample = SAMPLES_DIR / "parts_v1_sample.csv"
    with open(sample, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["partNo", "partName", "cat", "measure", "partStatus"])
        for r in rows[:50]:
            writer.writerow(list(r))


def export_parts_v2(db) -> None:
    """Current schema with drifted columns (extra 'legacy_ref' column, reordered)."""
    rows = db.execute(
        text(
            "SELECT part_number, name, uom, category, status, superseded_by, created_at "
            "FROM parts LIMIT 2000"
        )
    ).fetchall()
    out = OUT_DIR / "parts_v2.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Drifted: extra legacy_ref column, 'uom' moved before 'category'
        writer.writerow(
            [
                "part_number",
                "name",
                "uom",
                "category",
                "status",
                "superseded_by",
                "created_at",
                "legacy_ref",
            ]
        )
        for r in rows:
            writer.writerow(list(r) + [None])  # legacy_ref always null
    print(f"[export] {out} ({len(rows)} rows)")

    sample = SAMPLES_DIR / "parts_v2_sample.csv"
    with open(sample, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "part_number",
                "name",
                "uom",
                "category",
                "status",
                "superseded_by",
                "created_at",
                "legacy_ref",
            ]
        )
        for r in rows[:50]:
            writer.writerow(list(r) + [None])


def export_change_orders_xlsx(db) -> None:
    """change_orders.xlsx — requires openpyxl; skips gracefully if not installed."""
    try:
        import openpyxl
    except ImportError:
        print("[export] openpyxl not installed — skipping change_orders.xlsx")
        return

    rows = db.execute(
        text(
            "SELECT co_number, state, priority, description, requested_by, "
            "opened_at, closed_at FROM change_orders LIMIT 2000"
        )
    ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Change Orders"

    # Merged header rows (defect: row 1 is a section header, row 2 is column names)
    ws.append(
        ["MERIDIAN FABRICATION CO. — CHANGE ORDER EXPORT", None, None, None, None, None, None]
    )
    ws.merge_cells("A1:G1")
    ws.append(
        [
            "CO Number",
            "State",
            "Priority",
            "Description / Notes",
            "Requested By",
            "Opened",
            "Closed",
        ]
    )

    for r in rows:
        # Embedded newlines in description (defect)
        desc = (r[3] or "").replace(". ", ".\n") if r[3] else ""
        ws.append(
            [r[0], r[1], r[2], desc, r[4], str(r[5]) if r[5] else "", str(r[6]) if r[6] else ""]
        )

    out = OUT_DIR / "change_orders.xlsx"
    wb.save(out)
    print(f"[export] {out} ({len(rows)} rows)")


def export_suppliers_legacy(db) -> None:
    """suppliers_legacy.csv — Windows-1252 encoded (intentional encoding defect)."""
    rows = db.execute(
        text("SELECT name, code, country, contact_email FROM suppliers LIMIT 400")
    ).fetchall()

    out = OUT_DIR / "suppliers_legacy.csv"
    with open(out, "w", newline="", encoding="cp1252", errors="replace") as f:
        writer = csv.writer(f)
        writer.writerow(["supplier_name", "supplier_code", "country", "email"])
        for r in rows:
            writer.writerow(list(r))
    print(f"[export] {out} ({len(rows)} rows, Windows-1252 encoded)")

    sample = SAMPLES_DIR / "suppliers_legacy_sample.csv"
    # Sample committed as UTF-8 so it opens cleanly in the browser
    with open(sample, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["supplier_name", "supplier_code", "country", "email"])
        for r in rows[:50]:
            writer.writerow(list(r))


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    SAMPLES_DIR.mkdir(exist_ok=True)
    with SessionLocal() as db:
        export_parts_v1(db)
        export_parts_v2(db)
        export_change_orders_xlsx(db)
        export_suppliers_legacy(db)
    print("[export] Done.")


if __name__ == "__main__":
    main()
