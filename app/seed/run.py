"""Seed runner — populates the database from generators and writes mess_manifest.json.

Usage:
    python -m app.seed.run           # seed (idempotent — skips if already seeded)
    python -m app.seed.run --reset   # drop and reseed

All data is synthetic. Meridian Fabrication Co. is fictional.
"""

import sys

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.models import (  # noqa: F401 — needed for Base.metadata
    AuditLog,
    ChangeOrder,
    Part,
    PartRevision,
    PurchaseOrder,
    Supplier,
    User,
)
from app.seed import generators as gen
from app.seed.manifest import write_manifest


def _count_env(name: str, default: int) -> int:
    import os

    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _already_seeded(db) -> bool:
    try:
        count = db.execute(text("SELECT COUNT(*) FROM parts")).scalar()
        return count > 0
    except Exception:
        return False


def seed(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if not reset and _already_seeded(db):
            print("[seed] Database already seeded — skipping. Use --reset to reseed.")
            return

        if reset:
            print("[seed] Dropping existing data...")
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

        counts = {
            "users": _count_env("USERS_COUNT", 150),
            "parts": _count_env("PARTS_COUNT", 5000),
            "suppliers": _count_env("SUPPLIERS_COUNT", 400),
            "part_revisions_parts": _count_env("REVISION_PARTS_COUNT", 3000),
            "change_orders": _count_env("CHANGE_ORDERS_COUNT", 20000),
            "purchase_orders": _count_env("PURCHASE_ORDERS_COUNT", 30000),
            "audit_log": _count_env("AUDIT_LOG_COUNT", 200000),
        }
        stats: dict[str, int] = {}
        defect_records: dict[str, list[str | int]] = {}

        print("[seed] Generating users...")
        user_rows = gen.generate_users(counts["users"])
        db.bulk_insert_mappings(User, user_rows)
        db.flush()
        stats["users_count"] = len(user_rows)

        user_names = [u["name"] for u in user_rows]

        print("[seed] Generating parts...")
        part_rows = gen.generate_parts(counts["parts"], defects=defect_records)
        db.bulk_insert_mappings(Part, part_rows)
        db.flush()
        stats["parts_count"] = len(part_rows)

        part_ids = [r[0] for r in db.execute(text("SELECT id FROM parts")).fetchall()]

        print("[seed] Generating suppliers...")
        supplier_rows = gen.generate_suppliers(counts["suppliers"], defects=defect_records)
        db.bulk_insert_mappings(Supplier, supplier_rows)
        db.flush()
        stats["suppliers_count"] = len(supplier_rows)

        supplier_ids = [r[0] for r in db.execute(text("SELECT id FROM suppliers")).fetchall()]

        print("[seed] Generating part revisions...")
        rev_rows = gen.generate_revisions(
            part_ids[: counts["part_revisions_parts"]], defects=defect_records
        )
        db.bulk_insert_mappings(PartRevision, rev_rows)
        db.flush()
        stats["revisions_count"] = len(rev_rows)

        print("[seed] Generating change orders...")
        co_rows = gen.generate_change_orders(
            part_ids, user_names, counts["change_orders"], defects=defect_records
        )
        db.bulk_insert_mappings(ChangeOrder, co_rows)
        db.flush()
        stats["change_orders_count"] = len(co_rows)
        inactive_user_names = {row["name"] for row in user_rows if not row["active"]}
        defect_records["inactive_user_co_ref_count"] = [
            row["co_number"] for row in co_rows if row["requested_by"] in inactive_user_names
        ]

        print("[seed] Generating purchase orders...")
        po_rows = gen.generate_purchase_orders(
            supplier_ids, part_ids, counts["purchase_orders"], defects=defect_records
        )
        db.bulk_insert_mappings(PurchaseOrder, po_rows)
        db.flush()
        stats["purchase_orders_count"] = len(po_rows)
        inactive_suppliers = {
            supplier_id: row["code"]
            for supplier_id, row in zip(supplier_ids, supplier_rows, strict=True)
            if not row["active"]
        }
        referenced_supplier_ids = {row["supplier_id"] for row in po_rows}
        defect_records["defunct_supplier_count"] = [
            code
            for supplier_id, code in inactive_suppliers.items()
            if supplier_id in referenced_supplier_ids
        ]

        print("[seed] Generating audit log...")
        audit_rows = gen.generate_audit_log(
            {
                "parts": part_ids,
                "suppliers": supplier_ids,
                "change_orders": [r[0] for r in db.execute(text("SELECT id FROM change_orders"))],
                "purchase_orders": [
                    r[0] for r in db.execute(text("SELECT id FROM purchase_orders"))
                ],
            },
            user_names,
            counts["audit_log"],
            defects=defect_records,
        )
        db.bulk_insert_mappings(AuditLog, audit_rows)
        stats["audit_log_count"] = len(audit_rows)
        stats.update({name: len(records) for name, records in defect_records.items()})

        db.commit()

    print("[seed] Writing mess_manifest.json...")
    path = write_manifest(stats, defect_records)
    print(f"[seed] Done. Manifest: {path}")
    print(f"[seed] Row counts: {stats}")


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    seed(reset=reset_flag)
