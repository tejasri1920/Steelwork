# app/schemas/reports.py
#
# Pydantic schemas for the four report endpoints under GET /api/v1/reports/*.
#
# Each schema maps to one PostgreSQL view:
#   LotSummaryRow       → v_lot_summary            (AC1, AC2, AC7, AC8)
#   InspectionIssueRow  → v_inspection_issue_shipping (AC5, AC6)
#   IncompleteLotRow    → v_incomplete_lots         (AC4, AC10)
#   LineIssueRow        → v_issues_by_production_line (AC5)
#
# All schemas are read-only (returned from DB, never sent by client).
# Optional fields map to LEFT JOIN columns that can be NULL.

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class LotSummaryRow(BaseModel):
    """
    One row of the operational lot summary (v_lot_summary).

    Aggregates production, inspection, and shipping data into a single row per lot.
    This is the primary view used in meeting discussions (AC7).

    Columns sourced from:
      - lots (lot_id, start_date, end_date)
      - production_records aggregated (total_produced, lines_used)
      - inspection_records aggregated (any_issues, issue_count)
      - shipping_records aggregated (latest_status)
      - data_completeness (overall_completeness)

    Optional fields: NULL when a lot has no records in that domain yet.
    """

    model_config = ConfigDict(from_attributes=True)

    lot_id: int
    start_date: date
    end_date: date | None = None

    # Aggregated production columns — NULL if no production records
    total_produced: int | None = None  # SUM(quantity_produced)
    lines_used: str | None = None  # STRING_AGG of distinct production lines

    # Aggregated inspection columns — NULL if no inspection records
    any_issues: bool | None = None  # BOOL_OR(issue_flag)
    issue_count: int | None = None  # COUNT(*) FILTER (WHERE issue_flag)

    # Latest shipment status — NULL if no shipping records
    latest_status: str | None = None  # MAX(shipment_status) alphabetically

    overall_completeness: Decimal  # 0, 33, 67, or 100


class InspectionIssueRow(BaseModel):
    """
    One row of the inspection-issues-with-shipment view (v_inspection_issue_shipping).

    Lists lots that have at least one inspection issue, with their current shipment status.
    Supports AC5 (identify flagged lots) and AC6 (track those lots through shipping).

    The LEFT JOIN on shipping means ship_date, shipment_status, and destination
    will be NULL for flagged lots that haven't been shipped yet — making the gap visible.
    """

    model_config = ConfigDict(from_attributes=True)

    lot_id: int
    inspection_result: str  # 'Pass' | 'Fail' | 'Conditional'
    issue_flag: bool  # Always True in this view (filtered on issue_flag = TRUE)

    # NULL if no shipping record exists for this lot
    shipment_status: str | None = None
    ship_date: date | None = None
    destination: str | None = None


class IncompleteLotRow(BaseModel):
    """
    One row of the incomplete lots view (v_incomplete_lots).

    Shows every lot whose overall_completeness < 100, ordered by completeness ascending
    (most incomplete first). Supports AC4 (gaps visible) and AC10 (completeness score).
    """

    model_config = ConfigDict(from_attributes=True)

    lot_id: int
    start_date: date
    end_date: date | None = None
    has_production_data: bool
    has_inspection_data: bool
    has_shipping_data: bool
    overall_completeness: Decimal  # 0, 33, or 67 (never 100 — this view filters those out)


class LineIssueRow(BaseModel):
    """
    One row of the issues-by-production-line view (v_issues_by_production_line).

    Aggregates inspection issue counts per production line.
    Supports AC5 (which lines have the most problems).

    Columns:
        production_line    : Which line ('Line 1'–'Line 4').
        total_inspections  : COUNT of all inspection records tied to this line's lots.
        total_issues       : SUM of inspection records where issue_flag=True.
        issue_rate_pct     : (total_issues / total_inspections) * 100, rounded to 1 decimal.
    """

    model_config = ConfigDict(from_attributes=True)

    production_line: str
    total_inspections: int
    total_issues: int
    issue_rate_pct: Decimal  # e.g. 33.3 (one decimal place, from ROUND(...,1))
