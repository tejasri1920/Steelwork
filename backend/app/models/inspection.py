# app/models/inspection.py
#
# ORM model for the `inspection_records` table (ops schema).
#
# One row = one quality inspection performed on a specific lot.
# Supports AC1 (cross-function view), AC2 (lot alignment), AC5 (issue identification),
# AC6 (flagged lots → shipment status), AC9 (inspection results in detail view).

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class InspectionRecord(Base):
    """
    Maps to the `inspection_records` table in the ops schema.

    Columns:
        inspection_id    : Auto-incrementing primary key.
        lot_id           : Foreign key → lots.lot_id. Links this record to its lot.
        inspection_date  : Date the inspection was performed.
        inspector_id     : Employee ID of the inspector (string, e.g. 'EMP-042').
        inspection_result: Outcome — 'Pass', 'Fail', or 'Conditional'.
        issue_flag       : True when an issue was flagged (used in AC5, AC6).
        issue_category   : Type of defect — only set when issue_flag=True.
                           Values: 'Dimensional', 'Surface finish', 'Material defect',
                                   'Weld quality', 'Hardness', 'Other'
        defect_count     : Number of individual defects found in this inspection.
        sample_size      : How many units were sampled.
        notes            : Free-text inspector notes.
        created_at       : Row insert timestamp.
        updated_at       : Last update timestamp (maintained by DB trigger).

    Relationship:
        lot: The parent Lot this inspection belongs to.
    """

    __tablename__ = "inspection_records"

    inspection_id = Column(Integer, primary_key=True, index=True)

    # ForeignKey is required — tells SQLAlchemy how to JOIN inspection_records to lots.
    # Without it, relationship() cannot determine the join condition.
    lot_id = Column(Integer, ForeignKey("lots.lot_id"), nullable=False, index=True)

    inspection_date = Column(Date, nullable=False)
    inspector_id = Column(String(20), nullable=False)
    inspection_result = Column(String(20), nullable=False)  # 'Pass' | 'Fail' | 'Conditional'

    # Boolean stored as 0/1 in SQLite, true/false in PostgreSQL.
    # SQLAlchemy handles the conversion transparently.
    issue_flag = Column(Boolean, nullable=False, default=False)

    # NULL when issue_flag = False (no defect to categorize)
    issue_category = Column(String(50), nullable=True)

    defect_count = Column(Integer, nullable=False, default=0)
    sample_size = Column(Integer, nullable=False, default=1)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Back-reference: allows `record.lot` to navigate to the parent Lot object
    lot = relationship("Lot", back_populates="inspection_records")

    def __repr__(self) -> str:
        return (
            f"<InspectionRecord id={self.inspection_id} "
            f"lot={self.lot_id} result={self.inspection_result!r} flag={self.issue_flag}>"
        )
