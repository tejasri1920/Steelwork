# app/models/data_completeness.py
#
# ORM model for the `data_completeness` table (ops schema).
#
# This table is automatically maintained by PostgreSQL triggers whenever rows are
# inserted or deleted in production_records, inspection_records, or shipping_records.
# One row per lot — tracks whether each data domain is populated.
#
# Supports AC4 (missing data visibility) and AC10 (completeness score).

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import relationship

from app.database import Base


class DataCompleteness(Base):
    """
    Maps to the `data_completeness` table in the ops schema.

    This is a derived/summary table — do NOT insert or update rows manually.
    Rows are maintained automatically by the PostgreSQL trigger system:
      - trg_update_completeness_on_production
      - trg_update_completeness_on_inspection
      - trg_update_completeness_on_shipping

    In tests (SQLite), triggers don't run. Instead, the test helper
    `refresh_data_completeness()` replicates the same logic in Python.

    Columns:
        lot_id               : Primary key AND foreign key → lots.lot_id.
                               One row per lot (1:1 relationship).
        has_production_data  : True if ≥1 production_record exists for this lot.
        has_inspection_data  : True if ≥1 inspection_record exists for this lot.
        has_shipping_data    : True if ≥1 shipping_record exists for this lot.
        overall_completeness : Score 0–100.
                               ROUND((prod+insp+ship) / 3.0 * 100) → 0, 33, 67, or 100.
        updated_at           : Timestamp of the last completeness recalculation.

    Relationship:
        lot: The parent Lot this completeness row belongs to.
    """

    __tablename__ = "data_completeness"

    # lot_id is BOTH the primary key and the foreign key (1:1 with lots)
    lot_id = Column(Integer, ForeignKey("lots.lot_id"), primary_key=True)

    # Three boolean flags — one per data domain
    has_production_data = Column(Boolean, nullable=False, default=False)
    has_inspection_data = Column(Boolean, nullable=False, default=False)
    has_shipping_data = Column(Boolean, nullable=False, default=False)

    # Numeric(5,2) stores up to 999.99 — sufficient for a 0–100 percentage.
    # Using Numeric (not Float) avoids floating-point rounding errors.
    overall_completeness = Column(Numeric(5, 2), nullable=False, default=0)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Back-reference: allows `completeness.lot` to navigate to the parent Lot object
    # uselist=False enforces the 1:1 nature — returns a single object, not a list
    lot = relationship("Lot", back_populates="data_completeness")

    def __repr__(self) -> str:
        return (
            f"<DataCompleteness lot={self.lot_id} "
            f"completeness={self.overall_completeness}% "
            f"prod={self.has_production_data} "
            f"insp={self.has_inspection_data} "
            f"ship={self.has_shipping_data}>"
        )
