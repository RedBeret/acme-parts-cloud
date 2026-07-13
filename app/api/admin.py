"""Admin / ops endpoints."""

import os
import secrets
import subprocess
import sys
import threading

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/admin", tags=["admin"])
_reset_lock = threading.Lock()


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.post("/reset")
def reset(seed: int = 42, x_admin_reset_token: str | None = Header(default=None)):
    """Trigger an opt-in reseed. Runs synchronously and permits one reset at a time."""
    if os.getenv("ENABLE_ADMIN_RESET", "false").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=403, detail="Admin reset is disabled")
    expected_token = os.getenv("ADMIN_RESET_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="Admin reset token is not configured")
    if not x_admin_reset_token or not secrets.compare_digest(x_admin_reset_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid admin reset token")
    if not _reset_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A reset is already running")

    env = os.environ.copy()
    env["SEED"] = str(seed)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.seed.run", "--reset"],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Reset timed out") from exc
    finally:
        _reset_lock.release()

    if result.returncode != 0:
        return JSONResponse({"error": "Reset failed"}, status_code=500)
    return {"status": "reseeded", "seed": seed, "log": result.stdout[-500:]}
