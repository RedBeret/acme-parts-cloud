"""Ground-truth manifest writer.

Emits mess_manifest.json describing every defect injected during seeding.
This file is the 'answer key' PRD-2 uses to measure cleaning accuracy.
All data is synthetic.
"""

import json
import os
from datetime import datetime
from pathlib import Path


def write_manifest(stats: dict) -> Path:
    """Write mess_manifest.json to the repo root (or MANIFEST_PATH env var)."""
    manifest = {
        "generated_at": datetime.utcnow().isoformat(),
        "seed": int(os.getenv("SEED", "42")),
        "messiness": os.getenv("MESSINESS", "medium"),
        "synthetic_notice": "All data is synthetic. Meridian Fabrication Co. is fictional.",
        "defects": {
            "parts": {
                "part_number_format_drift": stats.get("part_fmt_drift_count", 0),
                "description": (
                    "Part numbers using legacy era formats (2019-PN-N or P{N}) "
                    "instead of current PN-{N:04d} scheme."
                ),
            },
            "part_revisions": {
                "scheme_mixing": stats.get("rev_scheme_mix_count", 0),
                "retroactive_dates": stats.get("rev_date_flip_count", 0),
                "description": (
                    "Rev codes mixing letter and numeric schemes within the same part. "
                    "Retroactive effective dates where revision predates predecessor."
                ),
            },
            "suppliers": {
                "near_duplicate_names": stats.get("supplier_dupe_count", 0),
                "invalid_emails": stats.get("bad_email_count", 0),
                "defunct_active_refs": stats.get("defunct_supplier_count", 0),
                "description": (
                    "Supplier names appearing in multiple casings/abbreviations. "
                    "Invalid or malformed contact email addresses. "
                    "Inactive suppliers still referenced in purchase orders."
                ),
            },
            "change_orders": {
                "state_vocabulary_inconsistency": stats.get("co_state_mess_count", 0),
                "impossible_dates": stats.get("co_date_flip_count", 0),
                "description": (
                    "State field using mixed vocabulary (open/OPEN/In-Work). "
                    "Closed timestamps before opened timestamps."
                ),
            },
            "purchase_orders": {
                "price_magnitude_errors": stats.get("price_error_count", 0),
                "mixed_currencies": stats.get("currency_mix_count", 0),
                "description": (
                    "Unit prices with magnitude errors (100x or 0.01x off). "
                    "Mixed currencies without conversion (compare at face value)."
                ),
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
    out_path.write_text(json.dumps(manifest, indent=2))
    return out_path
