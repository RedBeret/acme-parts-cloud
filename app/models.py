"""SQLAlchemy ORM models for AcmeParts Cloud.

Fictional company: Meridian Fabrication Co.
All data is synthetic.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    part_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64))
    uom: Mapped[str] = mapped_column(String(16))  # unit of measure
    status: Mapped[str] = mapped_column(String(32), default="active")
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    revisions: Mapped[list["PartRevision"]] = relationship(
        back_populates="part", cascade="all, delete-orphan"
    )
    change_orders: Mapped[list["ChangeOrder"]] = relationship(back_populates="part")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="part")


class PartRevision(Base):
    __tablename__ = "part_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), index=True)
    rev_code: Mapped[str] = mapped_column(String(16))
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    part: Mapped["Part"] = relationship(back_populates="revisions")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="supplier")


class ChangeOrder(Base):
    __tablename__ = "change_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    co_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="open")
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    part: Mapped["Part"] = relationship(back_populates="change_orders")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), index=True)
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    order_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    part: Mapped["Part"] = relationship(back_populates="purchase_orders")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(256), unique=True)
    role: Mapped[str] = mapped_column(String(64), default="engineer")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
