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

        stats: dict = {}

        print("[seed] Generating users...")
        user_rows = gen.generate_users(150)
        db.bulk_insert_mappings(User, user_rows)
        db.flush()
        stats["users_count"] = len(user_rows)

        user_names = [u["name"] for u in user_rows]

        print("[seed] Generating parts...")
        part_rows = gen.generate_parts(5000)
        db.bulk_insert_mappings(Part, part_rows)
        db.flush()
        stats["parts_count"] = len(part_rows)

        # Track format drift count for manifest
        current_era = [p for p in part_rows if p["part_number"].startswith("PN-")]
        stats["part_fmt_drift_count"] = stats["parts_count"] - len(current_era)

        part_ids = [r[0] for r in db.execute(text("SELECT id FROM parts")).fetchall()]

        print("[seed] Generating suppliers...")
        supplier_rows = gen.generate_suppliers(400)
        db.bulk_insert_mappings(Supplier, supplier_rows)
        db.flush()
        stats["suppliers_count"] = len(supplier_rows)
        stats["bad_email_count"] = sum(
            1 for s in supplier_rows if s["contact_email"] and "@" not in s["contact_email"]
        )
        stats["defunct_supplier_count"] = sum(1 for s in supplier_rows if not s["active"])

        supplier_ids = [r[0] for r in db.execute(text("SELECT id FROM suppliers")).fetchall()]

        print("[seed] Generating part revisions...")
        rev_rows = gen.generate_revisions(part_ids[:3000])  # revisions for first 3k parts
        db.bulk_insert_mappings(PartRevision, rev_rows)
        db.flush()
        stats["revisions_count"] = len(rev_rows)

        print("[seed] Generating change orders...")
        co_rows = gen.generate_change_orders(part_ids, user_names, 20000)
        db.bulk_insert_mappings(ChangeOrder, co_rows)
        db.flush()
        stats["change_orders_count"] = len(co_rows)
        stats["co_state_mess_count"] = sum(
            1
            for c in co_rows
            if c["state"] not in ("open", "in-review", "approved", "closed", "rejected")
        )
        stats["co_date_flip_count"] = sum(
            1
            for c in co_rows
            if c["closed_at"] and c["opened_at"] and c["closed_at"] < c["opened_at"]
        )

        print("[seed] Generating purchase orders...")
        po_rows = gen.generate_purchase_orders(supplier_ids, part_ids, 30000)
        db.bulk_insert_mappings(PurchaseOrder, po_rows)
        db.flush()
        stats["purchase_orders_count"] = len(po_rows)
        stats["price_error_count"] = sum(
            1 for p in po_rows if p["unit_price"] and p["unit_price"] > 50000
        )

        print("[seed] Writing audit log skeleton...")
        audit_rows = [
            {"entity": "parts", "entity_id": pid, "action": "create", "actor": None, "ts": None}
            for pid in part_ids[:5000]
        ]
        db.bulk_insert_mappings(AuditLog, audit_rows)
        stats["audit_log_count"] = len(audit_rows)

        db.commit()

    print("[seed] Writing mess_manifest.json...")
    path = write_manifest(stats)
    print(f"[seed] Done. Manifest: {path}")
    print(f"[seed] Row counts: {stats}")


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    seed(reset=reset_flag)
