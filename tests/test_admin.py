"""Admin reset safety tests."""

import subprocess

from fastapi.testclient import TestClient

from app.api import admin
from app.main import app

client = TestClient(app)


def test_reset_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_ADMIN_RESET", raising=False)
    response = client.post("/admin/reset?seed=99")
    assert response.status_code == 403


def test_reset_rejects_concurrent_run(monkeypatch):
    monkeypatch.setenv("ENABLE_ADMIN_RESET", "true")
    monkeypatch.setenv("ADMIN_RESET_TOKEN", "test-token")
    admin._reset_lock.acquire()
    try:
        response = client.post(
            "/admin/reset?seed=99", headers={"X-Admin-Reset-Token": "test-token"}
        )
    finally:
        admin._reset_lock.release()
    assert response.status_code == 409


def test_reset_passes_seed_in_child_environment(monkeypatch):
    monkeypatch.setenv("ENABLE_ADMIN_RESET", "true")
    monkeypatch.setenv("ADMIN_RESET_TOKEN", "test-token")
    monkeypatch.setenv("SEED", "42")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(admin.subprocess, "run", fake_run)
    response = client.post("/admin/reset?seed=99", headers={"X-Admin-Reset-Token": "test-token"})

    assert response.status_code == 200
    assert response.json()["seed"] == 99
    assert captured["env"]["SEED"] == "99"
    assert admin.os.environ["SEED"] == "42"


def test_reset_requires_valid_token(monkeypatch):
    monkeypatch.setenv("ENABLE_ADMIN_RESET", "true")
    monkeypatch.setenv("ADMIN_RESET_TOKEN", "test-token")
    response = client.post("/admin/reset?seed=99")
    assert response.status_code == 401
