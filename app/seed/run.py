"""Seed runner — populates the database from generators and writes mess_manifest.json.

Usage:
    python -m app.seed.run           # seed (idempotent — skips if already seeded)
    python -m app.seed.run --reset   # drop and reseed

All data is synthetic. Meridian Fabrication Co. is fictional.
"""

import sys
from collections import defaultdict

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


def _revision_defects(rows: list[dict]) -> tuple[int, int]:
    by_part: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_part[row["part_id"]].append(row)

    mixed_scheme_parts = 0
    retroactive_rows = 0
    for part_rows in by_part.values():
        codes = [str(row["rev_code"]) for row in part_rows]
        if any(code.isalpha() for code in codes) and any(code.isdigit() for code in codes):
            mixed_scheme_parts += 1

        previous = None
        for row in part_rows:
            effective_date = row["effective_date"]
            if previous and effective_date and effective_date < previous:
                retroactive_rows += 1
            if effective_date:
                previous = effective_date

    return mixed_scheme_parts, retroactive_rows


def _supplier_dupe_count(rows: list[dict]) -> int:
    suffixes = (" inc.", " llc", " ltd.", " co.", " corp.", " corporation")
    normalized = []
    for row in rows:
        name = " ".join(row["name"].lower().replace(".", "").split())
        for suffix in suffixes:
            if name.endswith(suffix.strip(".")):
                name = name[: -len(suffix.strip("."))].strip()
        normalized.append(name)
    return len(normalized) - len(set(normalized))


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
        stats: dict = {}

        print("[seed] Generating users...")
        user_rows = gen.generate_users(counts["users"])
        db.bulk_insert_mappings(User, user_rows)
        db.flush()
        stats["users_count"] = len(user_rows)

        user_names = [u["name"] for u in user_rows]

        print("[seed] Generating parts...")
        part_rows = gen.generate_parts(counts["parts"])
        db.bulk_insert_mappings(Part, part_rows)
        db.flush()
        stats["parts_count"] = len(part_rows)

        # Track format drift count for manifest
        current_era = [p for p in part_rows if p["part_number"].startswith("PN-")]
        stats["part_fmt_drift_count"] = stats["parts_count"] - len(current_era)

        part_ids = [r[0] for r in db.execute(text("SELECT id FROM parts")).fetchall()]

        print("[seed] Generating suppliers...")
        supplier_rows = gen.generate_suppliers(counts["suppliers"])
        db.bulk_insert_mappings(Supplier, supplier_rows)
        db.flush()
        stats["suppliers_count"] = len(supplier_rows)
        stats["supplier_dupe_count"] = _supplier_dupe_count(supplier_rows)
        stats["bad_email_count"] = sum(
            1 for s in supplier_rows if s["contact_email"] and "@" not in s["contact_email"]
        )
        stats["defunct_supplier_count"] = sum(1 for s in supplier_rows if not s["active"])

        supplier_ids = [r[0] for r in db.execute(text("SELECT id FROM suppliers")).fetchall()]

        print("[seed] Generating part revisions...")
        rev_rows = gen.generate_revisions(part_ids[: counts["part_revisions_parts"]])
        db.bulk_insert_mappings(PartRevision, rev_rows)
        db.flush()
        stats["revisions_count"] = len(rev_rows)
        stats["rev_scheme_mix_count"], stats["rev_date_flip_count"] = _revision_defects(rev_rows)

        print("[seed] Generating change orders...")
        co_rows = gen.generate_change_orders(part_ids, user_names, counts["change_orders"])
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
        po_rows = gen.generate_purchase_orders(supplier_ids, part_ids, counts["purchase_orders"])
        db.bulk_insert_mappings(PurchaseOrder, po_rows)
        db.flush()
        stats["purchase_orders_count"] = len(po_rows)
        stats["price_error_count"] = sum(
            1 for p in po_rows if p["unit_price"] and p["unit_price"] > 50000
        )
        stats["currency_mix_count"] = sum(1 for p in po_rows if p["currency"] != "USD")

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
        )
        db.bulk_insert_mappings(AuditLog, audit_rows)
        stats["audit_log_count"] = len(audit_rows)
        stats["audit_missing_actor_count"] = sum(1 for row in audit_rows if row["actor"] is None)

        db.commit()

    print("[seed] Writing mess_manifest.json...")
    path = write_manifest(stats)
    print(f"[seed] Done. Manifest: {path}")
    print(f"[seed] Row counts: {stats}")


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    seed(reset=reset_flag)
