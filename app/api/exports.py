"""Messy export download endpoints."""

import csv
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/exports", tags=["exports"])


def _attachment_headers(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


def _csv_response(
    filename: str,
    headers: list[str],
    rows,
    *,
    encoding: str = "utf-8",
) -> Response:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    body = buffer.getvalue().encode(encoding, errors="replace")
    return Response(
        body,
        media_type=f"text/csv; charset={encoding}",
        headers=_attachment_headers(filename),
    )


@router.get("/parts/v1")
def export_parts_v1(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT part_number, name, category, uom, status FROM parts LIMIT 2000")
    ).fetchall()
    return _csv_response(
        "parts_v1.csv",
        ["partNo", "partName", "cat", "measure", "partStatus"],
        rows,
    )


@router.get("/parts/v2")
def export_parts_v2(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT part_number, name, uom, category, status, superseded_by, created_at "
            "FROM parts LIMIT 2000"
        )
    ).fetchall()
    export_rows = [list(row) + [None] for row in rows]
    return _csv_response(
        "parts_v2.csv",
        [
            "part_number",
            "name",
            "uom",
            "category",
            "status",
            "superseded_by",
            "created_at",
            "legacy_ref",
        ],
        export_rows,
    )


@router.get("/suppliers/legacy")
def export_suppliers_legacy(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT name, code, country, contact_email FROM suppliers LIMIT 400")
    ).fetchall()
    return _csv_response(
        "suppliers_legacy.csv",
        ["supplier_name", "supplier_code", "country", "email"],
        rows,
        encoding="cp1252",
    )


@router.get("/change-orders")
@router.get("/change-orders.xlsx")
def export_change_orders_xlsx(db: Session = Depends(get_db)):
    import openpyxl

    rows = db.execute(
        text(
            "SELECT co_number, state, priority, description, requested_by, "
            "opened_at, closed_at FROM change_orders LIMIT 2000"
        )
    ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Change Orders"
    ws.append(["MERIDIAN FABRICATION CO. CHANGE ORDER EXPORT", None, None, None, None, None, None])
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

    for row in rows:
        desc = (row[3] or "").replace(". ", ".\n") if row[3] else ""
        ws.append(
            [
                row[0],
                row[1],
                row[2],
                desc,
                row[4],
                str(row[5]) if row[5] else "",
                str(row[6]) if row[6] else "",
            ]
        )

    out = BytesIO()
    wb.save(out)
    return Response(
        out.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_attachment_headers("change_orders.xlsx"),
    )
