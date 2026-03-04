# app/models/shipping.py
#
# ORM model for the `shipping_records` table (ops schema).
#
# One row = one shipment dispatched for a specific lot.
# Supports AC1 (cross-function view), AC2 (lot alignment), AC6 (flagged lots → shipment
# status), AC8 (shipment status), AC9 (shipping details in lot drill-down).

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class ShippingRecord(Base):
    """
    Maps to the `shipping_records` table in the ops schema.

    Columns:
        shipping_id      : Auto-incrementing primary key.
        lot_id           : Foreign key → lots.lot_id. Links this shipment to its lot.
        ship_date        : Date the shipment was dispatched.
        carrier          : Carrier name (e.g., 'FedEx Freight', 'UPS LTL').
        tracking_number  : Carrier tracking number (nullable — may not be available yet).
        destination      : Destination city/facility (e.g., 'Detroit Assembly Plant').
        quantity_shipped : Number of units included in this shipment.
        shipment_status  : Current state — 'Pending', 'In Transit', 'Delivered', 'On Hold'.
        notes            : Free-text shipping coordinator notes.
        created_at       : Row insert timestamp.
        updated_at       : Last update timestamp (maintained by DB trigger).

    Relationship:
        lot: The parent Lot this shipment belongs to.
    """

    __tablename__ = "shipping_records"

    shipping_id = Column(Integer, primary_key=True, index=True)

    # ForeignKey is required — tells SQLAlchemy how to JOIN shipping_records to lots.
    # Without it, relationship() cannot determine the join condition.
    lot_id = Column(Integer, ForeignKey("lots.lot_id"), nullable=False, index=True)

    ship_date = Column(Date, nullable=False)
    carrier = Column(String(100), nullable=False)

    # NULL until the carrier provides a tracking number
    tracking_number = Column(String(100), nullable=True)

    destination = Column(String(200), nullable=False)
    quantity_shipped = Column(Integer, nullable=False)

    # 'Pending' | 'In Transit' | 'Delivered' | 'On Hold'
    shipment_status = Column(String(30), nullable=False, default="Pending")

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Back-reference: allows `record.lot` to navigate to the parent Lot object
    lot = relationship("Lot", back_populates="shipping_records")

    def __repr__(self) -> str:
        return (
            f"<ShippingRecord id={self.shipping_id} "
            f"lot={self.lot_id} status={self.shipment_status!r} dest={self.destination!r}>"
        )
