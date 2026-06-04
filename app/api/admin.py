"""Admin / ops endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.post("/reset")
def reset(seed: int = 42):
    """Trigger a reseed. Runs synchronously — may take 30–60s."""
    import os
    import subprocess

    os.environ["SEED"] = str(seed)
    result = subprocess.run(
        ["python", "-m", "app.seed.run", "--reset"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        return JSONResponse({"error": result.stderr}, status_code=500)
    return {"status": "reseeded", "seed": seed, "log": result.stdout[-500:]}
