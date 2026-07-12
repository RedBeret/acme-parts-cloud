"""AcmeParts Cloud — FastAPI application entry point.

Fictional company: Meridian Fabrication Co.
All data is synthetic.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from app.api import admin, change_orders, exports, parts, suppliers
from app.database import SessionLocal
from app.models import ChangeOrder, Part, Supplier

app = FastAPI(
    title="AcmeParts Cloud",
    description=("Synthetic enterprise sandbox — Meridian Fabrication Co. All data is fictional."),
    version="1.0.0",
)

# Anchor the template directory to this file so the app works regardless of
# the working directory uvicorn is launched from.
templates = Jinja2Templates(directory=str(Path(__file__).parent / "ui" / "templates"))

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(parts.router)
app.include_router(suppliers.router)
app.include_router(change_orders.router)
app.include_router(exports.router)
app.include_router(admin.router)


# ── UI routes (server-rendered Jinja2 + HTMX) ────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    with SessionLocal() as db:
        parts_count = db.query(func.count(Part.id)).scalar()
        suppliers_count = db.query(func.count(Supplier.id)).scalar()
        co_count = db.query(func.count(ChangeOrder.id)).scalar()
        open_cos = (
            db.query(func.count(ChangeOrder.id))
            .filter(ChangeOrder.state.in_(["open", "OPEN", "In-Work"]))
            .scalar()
        )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "parts_count": parts_count,
            "suppliers_count": suppliers_count,
            "co_count": co_count,
            "open_cos": open_cos,
        },
    )


@app.get("/parts", response_class=HTMLResponse)
def parts_list(request: Request, search: str = "", status: str = ""):
    with SessionLocal() as db:
        q = db.query(Part)
        if search:
            q = q.filter(Part.part_number.ilike(f"%{search}%"))
        if status:
            q = q.filter(Part.status == status)
        items = q.order_by(Part.id).limit(200).all()

    return templates.TemplateResponse(
        request,
        "parts.html",
        {
            "parts": items,
            "search": search,
            "status": status,
        },
    )


@app.get("/suppliers", response_class=HTMLResponse)
def suppliers_list(request: Request, search: str = ""):
    with SessionLocal() as db:
        q = db.query(Supplier)
        if search:
            q = q.filter(Supplier.name.ilike(f"%{search}%"))
        items = q.order_by(Supplier.id).limit(200).all()

    return templates.TemplateResponse(
        request,
        "suppliers.html",
        {
            "suppliers": items,
            "search": search,
        },
    )


@app.get("/change-orders", response_class=HTMLResponse)
def change_orders_list(request: Request, state: str = ""):
    with SessionLocal() as db:
        q = db.query(ChangeOrder)
        if state:
            q = q.filter(ChangeOrder.state == state)
        items = q.order_by(ChangeOrder.id.desc()).limit(200).all()

    return templates.TemplateResponse(
        request,
        "change_orders.html",
        {
            "change_orders": items,
            "state": state,
        },
    )
