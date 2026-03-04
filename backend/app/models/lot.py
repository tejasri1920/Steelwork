# app/models/lot.py
#
# ORM model for the `lots` table (ops schema).
#
# A "lot" is a production batch — a quantity of a specific part produced together.
# It is the central entity that ties Production, Inspection, and Shipping data
# together by lot_id (AC1, AC2).
#
# SQLAlchemy ORM primer:
#   - Each class maps to one database table.
#   - Column() declares a column; its type must match the SQL schema.
#   - relationship() declares a Python-level link — it does NOT add a DB column.
#     It allows `lot.production_records` to return a list of ProductionRecord objects.
#   - ForeignKey() is required for SQLAlchemy to know how to JOIN two tables.

from sqlalchemy import Column, Date, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Lot(Base):
    """
    Maps to the `lots` table in the ops schema.

    One row = one production lot (a batch of parts produced together).
    All child records (production runs, inspections, shipments) reference
    a lot by lot_id.

    Columns:
        lot_id    : Auto-incrementing integer primary key.
        lot_code  : Human-readable business identifier (e.g., "LOT-20260112-001").
                    UNIQUE — the same code is used across all source spreadsheets.
        start_date: Date the lot was first produced / opened.
        end_date  : Date the lot was closed. NULL while the lot is still in progress.
        created_at: Timestamp when this row was inserted (set automatically by the DB).
        updated_at: Timestamp of the last update (maintained by a DB trigger).

    Relationships:
        production_records : List of all production runs for this lot.
        inspection_records : List of all inspection events for this lot.
        shipping_records   : List of all shipment records for this lot.
        data_completeness  : One completeness summary row for this lot (one-to-one).
    """

    __tablename__ = "lots"
    # Note: no schema="ops" here. Instead, search_path=ops is set on the
    # PostgreSQL connection in database.py. This keeps the model compatible
    # with both PostgreSQL (production) and SQLite (tests).

    lot_id = Column(Integer, primary_key=True, index=True)
    lot_code = Column(String(50), nullable=False, unique=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # NULL while lot is open
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    # lazy="select": SQLAlchemy does NOT load these automatically when you load
    # a Lot. You must explicitly request them (e.g., via selectinload in queries).
    # This prevents the N+1 problem: loading 100 lots doesn't fire 100+ extra queries.

    production_records = relationship(
        "ProductionRecord",  # String reference avoids circular import
        back_populates="lot",  # Bidirectional: ProductionRecord.lot → this Lot
        lazy="select",
    )
    inspection_records = relationship(
        "InspectionRecord",
        back_populates="lot",
        lazy="select",
    )
    shipping_records = relationship(
        "ShippingRecord",
        back_populates="lot",
        lazy="select",
    )
    data_completeness = relationship(
        "DataCompleteness",
        back_populates="lot",
        uselist=False,  # One-to-one: each lot has exactly one completeness row
        lazy="select",
    )

    def __repr__(self) -> str:
        # __repr__ is what Python shows when you print() or inspect a Lot object
        return f"<Lot id={self.lot_id} code={self.lot_code!r}>"
