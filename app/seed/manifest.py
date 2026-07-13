"""Ground-truth manifest writer.

Emits mess_manifest.json describing every defect injected during seeding.
This file is the 'answer key' PRD-2 uses to measure cleaning accuracy.
All data is synthetic.
"""

import json
import os
from pathlib import Path

DEFECT_RECORD_KEYS = (
    "part_fmt_drift_count",
    "rev_scheme_mix_count",
    "rev_date_flip_count",
    "supplier_dupe_count",
    "bad_email_count",
    "defunct_supplier_count",
    "inactive_user_co_ref_count",
    "co_state_mess_count",
    "co_date_flip_count",
    "price_error_count",
    "currency_mix_count",
    "audit_missing_actor_count",
)


def write_manifest(stats: dict, defect_records: dict[str, list[str | int]] | None = None) -> Path:
    """Write counts and stable record identifiers for every injected defect."""
    supplied_records = defect_records or {}
    records = {name: list(supplied_records.get(name, [])) for name in DEFECT_RECORD_KEYS}
    counts = {name: len(ids) for name, ids in records.items()}
    manifest = {
        "manifest_version": 2,
        "seed": int(os.getenv("SEED", "42")),
        "messiness": os.getenv("MESSINESS", "medium"),
        "synthetic_notice": "All data is synthetic. Meridian Fabrication Co. is fictional.",
        "defect_counts": dict(sorted(counts.items())),
        "defect_records": dict(sorted(records.items())),
        "defects": {
            "parts": {
                "part_number_format_drift": counts["part_fmt_drift_count"],
                "description": (
                    "Part numbers using legacy era formats (2019-PN-N or P{N}) "
                    "instead of current PN-{N:04d} scheme."
                ),
            },
            "part_revisions": {
                "scheme_mixing": counts["rev_scheme_mix_count"],
                "retroactive_dates": counts["rev_date_flip_count"],
                "description": (
                    "Rev codes mixing letter and numeric schemes within the same part. "
                    "Retroactive effective dates where revision predates predecessor."
                ),
            },
            "suppliers": {
                "near_duplicate_names": counts["supplier_dupe_count"],
                "invalid_emails": counts["bad_email_count"],
                "defunct_active_refs": counts["defunct_supplier_count"],
                "description": (
                    "Supplier names appearing in multiple casings/abbreviations. "
                    "Invalid or malformed contact email addresses. "
                    "Inactive suppliers still referenced in purchase orders."
                ),
            },
            "users": {
                "change_orders_referencing_inactive_users": counts["inactive_user_co_ref_count"],
                "description": "Change orders requested by users who are now inactive.",
            },
            "change_orders": {
                "state_vocabulary_inconsistency": counts["co_state_mess_count"],
                "impossible_dates": counts["co_date_flip_count"],
                "description": (
                    "State field using mixed vocabulary (open/OPEN/In-Work). "
                    "Closed timestamps before opened timestamps."
                ),
            },
            "purchase_orders": {
                "price_magnitude_errors": counts["price_error_count"],
                "mixed_currencies": counts["currency_mix_count"],
                "description": (
                    "Unit prices with injected magnitude errors (100x, 0.01x, or 1000x). "
                    "Mixed currencies without conversion (compare at face value)."
                ),
            },
            "audit_log": {
                "missing_actors": counts["audit_missing_actor_count"],
                "description": "Rows without an actor.",
            },
            "exports": {
                "parts_v1_legacy_headers": True,
                "parts_v2_schema_drift": True,
                "change_orders_merged_header": True,
                "change_orders_embedded_newlines": True,
                "suppliers_legacy_encoding": "cp1252",
                "description": "Intentional schema, layout, and encoding defects in exports.",
            },
        },
        "row_counts": {
            "parts": stats.get("parts_count", 0),
            "part_revisions": stats.get("revisions_count", 0),
            "suppliers": stats.get("suppliers_count", 0),
            "change_orders": stats.get("change_orders_count", 0),
            "purchase_orders": stats.get("purchase_orders_count", 0),
            "users": stats.get("users_count", 0),
            "audit_log": stats.get("audit_log_count", 0),
        },
    }

    out_path = Path(os.getenv("MANIFEST_PATH", "mess_manifest.json"))
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return out_path
