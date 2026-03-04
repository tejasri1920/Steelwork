# app/schemas/lot.py
#
# Pydantic schemas for the Lot API endpoints.
#
# These are the shapes of data returned by GET /api/v1/lots and
# GET /api/v1/lots/{lot_code}.
#
# Pydantic schemas serve two purposes:
#   1. Validation — FastAPI auto-validates response data against these shapes.
#   2. Serialization — SQLAlchemy ORM objects are converted to JSON via these schemas.
#
# Naming convention:
#   *Out  — schemas for nested child objects returned inside a parent schema
#   LotSummary  — lightweight row returned by the lots list endpoint (AC2, AC3)
#   LotDetail   — full drill-down returned by the lot detail endpoint (AC9)

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# ── Child record schemas ──────────────────────────────────────────────────────
# These are embedded inside LotDetail to show full child records for a lot.


class ProductionRecordOut(BaseModel):
    """
    Serializes a single production_records row inside a LotDetail response.

    All fields are read-only (returned from DB, never sent by client).
    Optional fields map to nullable DB columns.
    """

    # Pydantic v2: model_config replaces the inner class Config
    # from_attributes=True allows Pydantic to read values from SQLAlchemy ORM objects
    # (which use attribute access) instead of dict-style access.
    model_config = ConfigDict(from_attributes=True)

    production_id: int
    production_date: date
    production_line: str  # 'Line 1'–'Line 4'
    quantity_produced: int
    shift: str  # 'Day' | 'Swing' | 'Night'
    part_number: str
    units_planned: int
    downtime_min: int  # Minutes of unplanned downtime (≥0)
    line_issue: bool
    primary_issue: str | None = None  # None when line_issue=False
    supervisor_notes: str | None = None


class InspectionRecordOut(BaseModel):
    """
    Serializes a single inspection_records row inside a LotDetail response.
    Supports AC5 (issue identification) and AC9 (full drill-down).
    """

    model_config = ConfigDict(from_attributes=True)

    inspection_id: int
    inspection_date: date
    inspector_id: str
    inspection_result: str  # 'Pass' | 'Fail' | 'Conditional'
    issue_flag: bool
    issue_category: str | None = None  # None when issue_flag=False
    defect_count: int
    sample_size: int
    notes: str | None = None


class ShippingRecordOut(BaseModel):
    """
    Serializes a single shipping_records row inside a LotDetail response.
    Supports AC6 (flagged lots → shipment status) and AC8 (shipment status).
    """

    model_config = ConfigDict(from_attributes=True)

    shipping_id: int
    ship_date: date
    carrier: str
    tracking_number: str | None = None  # None until carrier provides it
    destination: str
    quantity_shipped: int
    shipment_status: str  # 'Pending' | 'In Transit' | 'Delivered' | 'On Hold'
    notes: str | None = None


# ── Top-level lot schemas ─────────────────────────────────────────────────────


class LotSummary(BaseModel):
    """
    Lightweight lot row returned by GET /api/v1/lots (list endpoint).

    Contains only the lot header fields plus the completeness score.
    Supports AC2 (lots visible by lot_code), AC3 (date filtering on start_date),
    AC4 (completeness score visible in list), AC10 (missing data surfaced).

    Time complexity: O(1) per row (no child data loaded).
    """

    model_config = ConfigDict(from_attributes=True)

    lot_id: int
    lot_code: str  # Human-readable identifier, e.g. 'LOT-20260112-001'
    start_date: date
    end_date: date | None = None  # None for lots still in progress

    # Completeness fields — derived from the data_completeness table
    has_production_data: bool
    has_inspection_data: bool
    has_shipping_data: bool
    overall_completeness: Decimal  # 0, 33, 67, or 100


class LotDetail(BaseModel):
    """
    Full lot drill-down returned by GET /api/v1/lots/{lot_code}.

    Contains the lot header plus all child records (production, inspection, shipping)
    and the completeness summary.
    Supports AC9 (full lot detail view).

    Time complexity: O(P + I + S) where P, I, S are counts of child records.
    Space complexity: O(P + I + S) — all child records held in memory.
    """

    model_config = ConfigDict(from_attributes=True)

    lot_id: int
    lot_code: str
    start_date: date
    end_date: date | None = None

    # Child record lists — empty list ([]) when no records exist for that domain
    production_records: list[ProductionRecordOut] = []
    inspection_records: list[InspectionRecordOut] = []
    shipping_records: list[ShippingRecordOut] = []

    # Completeness summary (always present — every lot has a data_completeness row)
    has_production_data: bool
    has_inspection_data: bool
    has_shipping_data: bool
    overall_completeness: Decimal

    # Audit timestamps from the lots table
    created_at: datetime
    updated_at: datetime
