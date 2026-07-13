"""Tests for seed determinism and data quality properties.

These tests run without Docker — they exercise the generator functions directly.
All data is synthetic.
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SEED", "42")
os.environ.setdefault("MESSINESS", "medium")


from app.seed.generators import (
    generate_audit_log,
    generate_change_orders,
    generate_parts,
    generate_purchase_orders,
    generate_revisions,
    generate_suppliers,
    generate_users,
)

# ── Determinism ───────────────────────────────────────────────────────────────


def test_parts_deterministic():
    """Same seed → same output."""
    a = generate_parts(100)
    b = generate_parts(100)
    assert [p["part_number"] for p in a] == [p["part_number"] for p in b]


def test_suppliers_deterministic():
    a = generate_suppliers(50)
    b = generate_suppliers(50)
    assert [s["code"] for s in a] == [s["code"] for s in b]


def test_change_orders_deterministic():
    generate_parts(20)
    users = generate_users(10)
    part_ids = list(range(1, 21))
    user_names = [u["name"] for u in users]
    a = generate_change_orders(part_ids, user_names, 100)
    b = generate_change_orders(part_ids, user_names, 100)
    assert [c["co_number"] for c in a] == [c["co_number"] for c in b]


# ── Row counts ────────────────────────────────────────────────────────────────


def test_parts_count():
    parts = generate_parts(5000)
    assert len(parts) == 5000
    part_numbers = {row["part_number"] for row in parts}
    assert all(
        row["superseded_by"] is None or row["superseded_by"] in part_numbers for row in parts
    )
    assert all(row["superseded_by"] != row["part_number"] for row in parts)


def test_suppliers_count():
    suppliers = generate_suppliers(400)
    assert len(suppliers) == 400
    # All codes unique
    codes = [s["code"] for s in suppliers]
    assert len(codes) == len(set(codes))


def test_users_count():
    users = generate_users(150)
    assert len(users) == 150
    emails = [u["email"] for u in users]
    assert len(emails) == len(set(emails))


def test_numeric_revision_codes_are_numeric_ordered():
    revisions = generate_revisions(list(range(1, 100)))
    by_part = {}
    for row in revisions:
        by_part.setdefault(row["part_id"], []).append(row["rev_code"])
    for codes in by_part.values():
        if all(code.isdigit() for code in codes):
            assert codes == sorted(codes, key=int)


# ── Messiness properties ──────────────────────────────────────────────────────


def test_parts_have_format_drift():
    """Medium messiness should produce some legacy-format part numbers."""
    parts = generate_parts(5000)
    drift = [p for p in parts if not p["part_number"].startswith("PN-")]
    assert len(drift) > 0, "Expected some legacy-format part numbers in medium messiness"


def test_suppliers_have_bad_emails():
    """Medium messiness should produce some malformed emails."""
    defects: dict[str, list[str | int]] = {}
    suppliers = generate_suppliers(400, defects=defects)
    by_code = {row["code"]: row for row in suppliers}
    assert defects["bad_email_count"]
    assert all(code in by_code for code in defects["bad_email_count"])


def test_change_orders_have_state_mess():
    """Medium messiness should produce mixed-vocabulary state values."""
    generate_parts(50)
    users = generate_users(10)
    part_ids = list(range(1, 51))
    user_names = [u["name"] for u in users]
    cos = generate_change_orders(part_ids, user_names, 500)
    clean_states = {"open", "in-review", "approved", "closed", "rejected"}
    messy = [c for c in cos if c["state"] not in clean_states]
    assert len(messy) > 0, "Expected mixed state vocabulary in medium messiness"


def test_defect_records_are_stable_and_identify_rows():
    defects: dict[str, list[str | int]] = {}
    parts = generate_parts(200, defects=defects)
    suppliers = generate_suppliers(100, defects=defects)
    revisions = generate_revisions(list(range(1, 51)), defects=defects)
    users = generate_users(20)
    change_orders = generate_change_orders(
        list(range(1, 201)), [u["name"] for u in users], 300, defects=defects
    )
    generate_purchase_orders(list(range(1, 101)), list(range(1, 201)), 500, defects=defects)
    generate_audit_log(
        {"parts": list(range(1, 201))}, [u["name"] for u in users], 500, defects=defects
    )

    assert set(defects["part_fmt_drift_count"]) == {
        p["part_number"] for p in parts if not p["part_number"].startswith("PN-")
    }
    supplier_codes = {s["code"] for s in suppliers}
    assert set(defects["bad_email_count"]) <= supplier_codes
    by_supplier_code = {row["code"]: row for row in suppliers}
    assert all(
        by_supplier_code[code]["contact_email"].count("@") != 1
        or by_supplier_code[code]["contact_email"].endswith(".invalid")
        for code in defects["bad_email_count"]
    )
    duplicate_targets = {pair.split("->", 1)[0] for pair in defects["supplier_dupe_count"]}
    duplicate_sources = {pair.split("->", 1)[1] for pair in defects["supplier_dupe_count"]}
    assert duplicate_targets <= supplier_codes
    assert duplicate_sources <= supplier_codes
    previous_revision_date = {}
    observed_retroactive = set()
    for row in revisions:
        previous = previous_revision_date.get(row["part_id"])
        if previous is not None and row["effective_date"] < previous:
            observed_retroactive.add(f"{row['part_id']}:{row['rev_code']}")
        previous_revision_date[row["part_id"]] = row["effective_date"]
    assert set(defects["rev_date_flip_count"]) == observed_retroactive
    dirty_cos = {
        row["co_number"]
        for row in change_orders
        if row["state"] not in {"open", "in-review", "approved", "closed", "rejected"}
    }
    assert set(defects["co_state_mess_count"]) == dirty_cos
    assert all(1 <= row_id <= 500 for row_id in defects["price_error_count"])
    assert all(1 <= row_id <= 500 for row_id in defects["audit_missing_actor_count"])

    repeated: dict[str, list[str | int]] = {}
    generate_parts(200, defects=repeated)
    generate_suppliers(100, defects=repeated)
    generate_revisions(list(range(1, 51)), defects=repeated)
    generate_change_orders(list(range(1, 201)), [u["name"] for u in users], 300, defects=repeated)
    generate_purchase_orders(list(range(1, 101)), list(range(1, 201)), 500, defects=repeated)
    generate_audit_log(
        {"parts": list(range(1, 201))}, [u["name"] for u in users], 500, defects=repeated
    )
    assert defects == repeated


# ── Manifest ──────────────────────────────────────────────────────────────────


def test_manifest_written(tmp_path, monkeypatch):
    monkeypatch.setenv("MANIFEST_PATH", str(tmp_path / "mess_manifest.json"))
    from app.seed.manifest import write_manifest

    stats = {
        "parts_count": 100,
        "revisions_count": 300,
        "suppliers_count": 50,
        "change_orders_count": 200,
        "purchase_orders_count": 500,
        "users_count": 20,
        "audit_log_count": 100,
        "part_fmt_drift_count": 5,
        "bad_email_count": 3,
    }
    defect_records = {"bad_email_count": ["SUP-0001", "SUP-0002", "SUP-0003"]}
    path = write_manifest(stats, defect_records)
    assert path.exists()
    import json

    data = json.loads(path.read_text())
    assert data["seed"] == 42
    assert data["manifest_version"] == 2
    assert data["row_counts"]["parts"] == 100
    assert "defects" in data
    assert data["defects"]["suppliers"]["invalid_emails"] == 3
    assert data["defect_counts"]["bad_email_count"] == 3
    assert data["defect_records"]["bad_email_count"] == defect_records["bad_email_count"]


def test_manifest_counts_ignore_conflicting_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("MANIFEST_PATH", str(tmp_path / "mess_manifest.json"))
    from app.seed.manifest import write_manifest

    path = write_manifest({"bad_email_count": 999}, {"bad_email_count": ["SUP-0001", "SUP-0002"]})
    import json

    data = json.loads(path.read_text())
    assert data["defect_counts"]["bad_email_count"] == 2
    assert data["defects"]["suppliers"]["invalid_emails"] == 2


def test_reduced_seed_reconciles_manifest(tmp_path):
    import json
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path

    db_path = tmp_path / "seed.db"
    manifest_path = tmp_path / "mess_manifest.json"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{db_path}",
            "MANIFEST_PATH": str(manifest_path),
            "PARTS_COUNT": "100",
            "SUPPLIERS_COUNT": "30",
            "USERS_COUNT": "15",
            "REVISION_PARTS_COUNT": "50",
            "CHANGE_ORDERS_COUNT": "120",
            "PURCHASE_ORDERS_COUNT": "200",
            "AUDIT_LOG_COUNT": "250",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "app.seed.run", "--reset"],
        cwd=Path(__file__).parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(manifest_path.read_text())
    assert data["manifest_version"] == 2
    assert set(data["defect_counts"]) == set(data["defect_records"])
    assert all(
        data["defect_counts"][name] == len(records)
        for name, records in data["defect_records"].items()
    )
    with sqlite3.connect(db_path) as db:
        defunct_codes = {
            row[0]
            for row in db.execute(
                "SELECT DISTINCT s.code FROM suppliers s "
                "JOIN purchase_orders po ON po.supplier_id = s.id WHERE s.active = 0"
            )
        }
        inactive_user_cos = {
            row[0]
            for row in db.execute(
                "SELECT co.co_number FROM change_orders co "
                "WHERE co.requested_by IN (SELECT name FROM users WHERE active = 0)"
            )
        }
    assert set(data["defect_records"]["defunct_supplier_count"]) == defunct_codes
    assert set(data["defect_records"]["inactive_user_co_ref_count"]) == inactive_user_cos


def test_legacy_supplier_encoding_is_observable():
    from app.api.exports import _csv_response

    response = _csv_response(
        "suppliers_legacy.csv",
        ["supplier_name"],
        [["Élan Components"]],
        encoding="cp1252",
    )
    assert response.body.decode("cp1252").endswith("Élan Components\r\n")
    with pytest.raises(UnicodeDecodeError):
        response.body.decode("utf-8")


def test_manifest_is_byte_stable(tmp_path, monkeypatch):
    monkeypatch.setenv("MANIFEST_PATH", str(tmp_path / "mess_manifest.json"))
    from app.seed.manifest import write_manifest

    stats = {"parts_count": 10, "suppliers_count": 2, "bad_email_count": 1}
    path = write_manifest(stats)
    first = path.read_text()
    path = write_manifest(stats)
    second = path.read_text()
    assert first == second


# ── Export (schema only, no DB) ───────────────────────────────────────────────


def test_export_parts_v1_schema(tmp_path):
    """parts_v1.csv should use the legacy column names."""
    import csv
    import io

    from app.seed.generators import generate_parts

    parts = generate_parts(10)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["partNo", "partName", "cat", "measure", "partStatus"])
    for p in parts:
        writer.writerow([p["part_number"], p["name"], p["category"], p["uom"], p["status"]])
    output.seek(0)
    reader = csv.DictReader(output)
    row = next(reader)
    assert "partNo" in row
    assert "part_number" not in row
