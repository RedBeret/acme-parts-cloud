"""Parts API router — CRUD + cursor pagination + search."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Part

router = APIRouter(prefix="/api/parts", tags=["parts"])


class PartOut(BaseModel):
    id: int
    part_number: str
    name: str
    category: str
    uom: str
    status: str
    superseded_by: Optional[str] = None

    model_config = {"from_attributes": True}


class PartCreate(BaseModel):
    part_number: str
    name: str
    category: str
    uom: str
    status: str = "active"
    superseded_by: Optional[str] = None


@router.get("", response_model=dict)
def list_parts(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    after: Optional[int] = Query(None, description="Cursor: last seen id"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """List parts with cursor pagination and optional filtering."""
    q = db.query(Part)
    if search:
        q = q.filter(
            or_(Part.part_number.ilike(f"%{search}%"),
                Part.name.ilike(f"%{search}%"))
        )
    if status:
        q = q.filter(Part.status == status)
    if category:
        q = q.filter(Part.category == category)
    if after:
        q = q.filter(Part.id > after)
    q = q.order_by(Part.id).limit(limit)
    items = q.all()
    next_cursor = items[-1].id if len(items) == limit else None
    return {"items": [PartOut.model_validate(p) for p in items], "next_cursor": next_cursor}


@router.get("/{part_id}", response_model=PartOut)
def get_part(part_id: int, db: Session = Depends(get_db)):
    part = db.get(Part, part_id)
    if not part:
        raise HTTPException(404, "Part not found")
    return PartOut.model_validate(part)


@router.post("", response_model=PartOut, status_code=201)
def create_part(body: PartCreate, db: Session = Depends(get_db)):
    part = Part(**body.model_dump())
    db.add(part)
    db.commit()
    db.refresh(part)
    return PartOut.model_validate(part)


@router.patch("/{part_id}", response_model=PartOut)
def update_part(part_id: int, body: dict, db: Session = Depends(get_db)):
    part = db.get(Part, part_id)
    if not part:
        raise HTTPException(404, "Part not found")
    for k, v in body.items():
        if hasattr(part, k):
            setattr(part, k, v)
    db.commit()
    db.refresh(part)
    return PartOut.model_validate(part)


@router.delete("/{part_id}", status_code=204)
def delete_part(part_id: int, db: Session = Depends(get_db)):
    part = db.get(Part, part_id)
    if not part:
        raise HTTPException(404, "Part not found")
    db.delete(part)
    db.commit()
