"""Change Orders API router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChangeOrder

router = APIRouter(prefix="/api/change-orders", tags=["change-orders"])


class ChangeOrderOut(BaseModel):
    id: int
    co_number: str
    part_id: int
    state: str
    priority: str
    description: Optional[str] = None
    requested_by: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("", response_model=dict)
def list_change_orders(
    search: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    after: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(ChangeOrder)
    if search:
        q = q.filter(
            or_(ChangeOrder.co_number.ilike(f"%{search}%"),
                ChangeOrder.description.ilike(f"%{search}%"))
        )
    if state:
        q = q.filter(ChangeOrder.state == state)
    if priority:
        q = q.filter(ChangeOrder.priority == priority)
    if after:
        q = q.filter(ChangeOrder.id > after)
    q = q.order_by(ChangeOrder.id).limit(limit)
    items = q.all()
    next_cursor = items[-1].id if len(items) == limit else None
    return {
        "items": [ChangeOrderOut.model_validate(c) for c in items],
        "next_cursor": next_cursor,
    }


@router.get("/{co_id}", response_model=ChangeOrderOut)
def get_change_order(co_id: int, db: Session = Depends(get_db)):
    co = db.get(ChangeOrder, co_id)
    if not co:
        raise HTTPException(404, "Change order not found")
    return ChangeOrderOut.model_validate(co)


@router.patch("/{co_id}", response_model=ChangeOrderOut)
def update_change_order(co_id: int, body: dict, db: Session = Depends(get_db)):
    co = db.get(ChangeOrder, co_id)
    if not co:
        raise HTTPException(404, "Change order not found")
    for k, v in body.items():
        if hasattr(co, k):
            setattr(co, k, v)
    db.commit()
    db.refresh(co)
    return ChangeOrderOut.model_validate(co)
