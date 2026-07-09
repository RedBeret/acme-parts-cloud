"""API smoke tests — run against a live seeded instance.

Skip these in CI (requires Docker + Postgres). Run locally with:
    docker compose up -d && pytest tests/test_api_smoke.py -v

All data is synthetic.
"""
import os

import pytest

SMOKE_URL = os.getenv("SMOKE_API_URL", "")

pytestmark = pytest.mark.skipif(
    not SMOKE_URL,
    reason="SMOKE_API_URL not set — skipping live API tests",
)


def test_healthz():
    import httpx
    r = httpx.get(f"{SMOKE_URL}/admin/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_parts_pagination():
    import httpx
    r = httpx.get(f"{SMOKE_URL}/api/parts", params={"limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) == 10
    assert "next_cursor" in data


def test_list_parts_search():
    import httpx
    r = httpx.get(f"{SMOKE_URL}/api/parts", params={"search": "PN-"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert all("PN-" in i["part_number"] for i in items)


def test_list_suppliers():
    import httpx
    r = httpx.get(f"{SMOKE_URL}/api/suppliers", params={"limit": 5})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 5


def test_list_change_orders():
    import httpx
    r = httpx.get(f"{SMOKE_URL}/api/change-orders", params={"limit": 5})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 5


def test_get_nonexistent_part():
    import httpx
    r = httpx.get(f"{SMOKE_URL}/api/parts/999999999")
    assert r.status_code == 404
