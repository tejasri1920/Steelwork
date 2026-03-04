# app/schemas/__init__.py
#
# Makes `schemas` a Python package.
# Re-exports all public schema classes for convenient single-import access.
#
# Usage:
#   from app.schemas import LotSummary, LotDetail
#   from app.schemas import LotSummaryRow, InspectionIssueRow

from app.schemas.lot import (
    InspectionRecordOut,
    LotDetail,
    LotSummary,
    ProductionRecordOut,
    ShippingRecordOut,
)
from app.schemas.reports import (
    IncompleteLotRow,
    InspectionIssueRow,
    LineIssueRow,
    LotSummaryRow,
)

__all__ = [
    # Lot schemas
    "LotSummary",
    "LotDetail",
    "ProductionRecordOut",
    "InspectionRecordOut",
    "ShippingRecordOut",
    # Report schemas
    "LotSummaryRow",
    "InspectionIssueRow",
    "IncompleteLotRow",
    "LineIssueRow",
]
