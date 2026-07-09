"""Suppliers API router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Supplier

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


class SupplierOut(BaseModel):
    id: int
    name: str
    code: str
    country: Optional[str] = None
    contact_email: Optional[str] = None
    active: bool

    model_config = {"from_attributes": True}


class SupplierCreate(BaseModel):
    name: str
    code: str
    country: Optional[str] = None
    contact_email: Optional[str] = None
    active: bool = True


@router.get("", response_model=dict)
def list_suppliers(
    search: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    after: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Supplier)
    if search:
        q = q.filter(
            or_(Supplier.name.ilike(f"%{search}%"),
                Supplier.code.ilike(f"%{search}%"))
        )
    if active is not None:
        q = q.filter(Supplier.active == active)
    if after:
        q = q.filter(Supplier.id > after)
    q = q.order_by(Supplier.id).limit(limit)
    items = q.all()
    next_cursor = items[-1].id if len(items) == limit else None
    return {"items": [SupplierOut.model_validate(s) for s in items], "next_cursor": next_cursor}


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    s = db.get(Supplier, supplier_id)
    if not s:
        raise HTTPException(404, "Supplier not found")
    return SupplierOut.model_validate(s)


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(body: SupplierCreate, db: Session = Depends(get_db)):
    s = Supplier(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return SupplierOut.model_validate(s)
