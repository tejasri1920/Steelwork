# app/models/production.py
#
# ORM model for the `production_records` table (ops schema).
#
# One row = one production run: a specific lot manufactured on a specific line
# during a specific shift on a given date.
# Supports AC1 (cross-function view), AC2 (lot alignment), AC3 (date filter),
# AC5 (production issue identification).

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ProductionRecord(Base):
    """
    Maps to the `production_records` table in the ops schema.

    Columns:
        production_id    : Auto-incrementing primary key.
        lot_id           : Foreign key → lots.lot_id. Links this run to its lot.
        production_date  : Date this run occurred (used for AC3 date filtering).
        production_line  : Which line ran: 'Line 1', 'Line 2', 'Line 3', 'Line 4'.
        quantity_produced: Actual units output (may be less than planned).
        shift            : 'Day', 'Swing', or 'Night'.
        part_number      : Part identifier (e.g., "SW-8091-A").
        units_planned    : Target output for this run.
        downtime_min     : Minutes of unplanned downtime. Default 0.
        line_issue       : True when a line problem was flagged (AC5 key field).
        primary_issue    : Category of problem — only set when line_issue=True.
                           Values: 'Tool wear', 'Sensor fault', 'Material shortage',
                                   'Changeover delay', 'Quality hold', 'Operator training'
        supervisor_notes : Free-text notes from the shift supervisor.
        created_at       : Row insert timestamp.
        updated_at       : Last update timestamp (maintained by DB trigger).

    Relationship:
        lot: The parent Lot this production run belongs to.
    """

    __tablename__ = "production_records"

    production_id = Column(Integer, primary_key=True, index=True)

    # ForeignKey is required — tells SQLAlchemy how to JOIN production_records to lots.
    # Without it, relationship() cannot determine the join condition.
    lot_id = Column(Integer, ForeignKey("lots.lot_id"), nullable=False, index=True)

    production_date = Column(Date, nullable=False)
    production_line = Column(String(50), nullable=False)  # 'Line 1'–'Line 4'
    quantity_produced = Column(Integer, nullable=False)
    shift = Column(String(20), nullable=False)  # 'Day' | 'Swing' | 'Night'
    part_number = Column(String(20), nullable=False)
    units_planned = Column(Integer, nullable=False)

    # SmallInteger uses 2 bytes instead of 4 — sufficient for downtime_min (max ~32767 min)
    downtime_min = Column(SmallInteger, nullable=False, default=0)

    # Boolean stored as 0/1 in SQLite, true/false in PostgreSQL.
    # SQLAlchemy handles the conversion transparently.
    line_issue = Column(Boolean, nullable=False, default=False)

    # NULL when line_issue = False (no issue to categorize)
    primary_issue = Column(String(50), nullable=True)

    supervisor_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Back-reference: allows `record.lot` to navigate to the parent Lot object
    lot = relationship("Lot", back_populates="production_records")

    def __repr__(self) -> str:
        return (
            f"<ProductionRecord id={self.production_id} "
            f"lot={self.lot_id} line={self.production_line!r} date={self.production_date}>"
        )
