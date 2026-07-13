"""Application metadata regression tests."""

from app.main import app


def test_openapi_version_matches_release() -> None:
    assert app.openapi()["info"]["version"] == "1.0.1"
