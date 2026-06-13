"""Tests for seed determinism and data quality properties.

These tests run without Docker — they exercise the generator functions directly.
All data is synthetic.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SEED", "42")
os.environ.setdefault("MESSINESS", "medium")


from app.seed.generators import (
    generate_change_orders,
    generate_parts,
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


# ── Messiness properties ──────────────────────────────────────────────────────


def test_parts_have_format_drift():
    """Medium messiness should produce some legacy-format part numbers."""
    parts = generate_parts(5000)
    drift = [p for p in parts if not p["part_number"].startswith("PN-")]
    assert len(drift) > 0, "Expected some legacy-format part numbers in medium messiness"


def test_suppliers_have_bad_emails():
    """Medium messiness should produce some malformed emails."""
    suppliers = generate_suppliers(400)
    bad = [s for s in suppliers if s["contact_email"] and "@" not in s["contact_email"]]
    assert len(bad) > 0, "Expected some malformed emails in medium messiness"


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
    path = write_manifest(stats)
    assert path.exists()
    import json

    data = json.loads(path.read_text())
    assert data["seed"] == 42
    assert data["row_counts"]["parts"] == 100
    assert "defects" in data
    assert data["defects"]["suppliers"]["invalid_emails"] == 3


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
