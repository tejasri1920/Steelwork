# app/routers/reports.py
#
# FastAPI router for analytical report endpoints.
#
# Registered at prefix /api/v1 in main.py, so full paths are:
#   GET /api/v1/reports/lot-summary          → lot_summary()
#   GET /api/v1/reports/inspection-issues    → inspection_issues()
#   GET /api/v1/reports/incomplete-lots      → incomplete_lots()
#   GET /api/v1/reports/line-issues          → line_issues()
#
# AC coverage:
#   AC1  — cross-function view (lot-summary combines prod + insp + ship)
#   AC4  — surface incomplete lots (incomplete-lots endpoint)
#   AC5  — production line issue rates (line-issues endpoint)
#   AC6  — flagged lots and their shipment status (inspection-issues endpoint)
#   AC7  — meeting-ready summary (lot-summary endpoint)
#   AC8  — shipment status overview (lot-summary endpoint)
#   AC10 — completeness scores in lot-summary and incomplete-lots
#
# Logging:
#   INFO  — each request with its query parameters
#   DEBUG — row counts returned to the caller

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import report_repo
from app.schemas.reports import (
    IncompleteLotRow,
    InspectionIssueRow,
    LineIssueRow,
    LotSummaryRow,
)

# Module-level logger.  Name follows __name__ convention: "app.routers.reports".
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],  # Groups all four endpoints under "reports" in Swagger UI
)


@router.get(
    "/lot-summary",
    response_model=list[LotSummaryRow],
    summary="Aggregated lot summary (one row per lot, all domains)",
    description=(
        "Returns one row per lot aggregating production totals, inspection issue flags, "
        "and latest shipment status. Designed for meeting discussions. "
        "Optional start_date / end_date query params filter by lot start_date. "
        "Supports AC1, AC3, AC7, AC8, AC10."
    ),
)
def lot_summary(
    start_date: date | None = Query(
        default=None,
        description="Include only lots whose start_date ≥ this date (ISO-8601).",
    ),
    end_date: date | None = Query(
        default=None,
        description="Include only lots whose start_date ≤ this date (ISO-8601).",
    ),
    db: Session = Depends(get_db),
) -> list[LotSummaryRow]:
    """
    Return the aggregated operational lot summary, optionally filtered by date range.

    Query parameters:
        start_date: Filter — only lots with start_date ≥ this value.
        end_date:   Filter — only lots with start_date ≤ this value.

    Returns:
        HTTP 200 with a JSON array of LotSummaryRow objects.
        Empty array [] if no lots match the filter.

    AC1:  Shows all three data domains side-by-side for each lot.
    AC3:  Date range filter wired to this endpoint.
    AC7:  One row per lot — clean format for meeting discussions.
    AC8:  latest_status column shows current shipment state.
    AC10: overall_completeness included in each row.
    """
    logger.info(
        "GET /reports/lot-summary | start_date=%s end_date=%s",
        start_date,
        end_date,
    )

    # model_validate converts each plain dict from the repo into a typed Pydantic
    # object, satisfying mypy's return type check and giving FastAPI a fully
    # validated object to serialise.
    rows = [
        LotSummaryRow.model_validate(row)
        for row in report_repo.get_lot_summary(db, start_date=start_date, end_date=end_date)
    ]

    logger.debug("GET /reports/lot-summary returned %d row(s)", len(rows))
    return rows


@router.get(
    "/inspection-issues",
    response_model=list[InspectionIssueRow],
    summary="Lots with inspection issues and their shipment status",
    description=(
        "Returns all lots that have at least one flagged inspection record, "
        "joined with their shipment status. NULL shipment fields mean the lot "
        "has not been shipped yet. Supports AC5 and AC6."
    ),
)
def inspection_issues(db: Session = Depends(get_db)) -> list[InspectionIssueRow]:
    """
    Return all inspection-flagged lots with their current shipment status.

    Returns:
        HTTP 200 with a JSON array of InspectionIssueRow objects.
        Empty array [] if no flagged inspection records exist.

    AC5: Identify lots that had inspection problems.
    AC6: Track those lots to see if they were held, rerouted, or shipped.
    """
    logger.info("GET /reports/inspection-issues")

    rows = [InspectionIssueRow.model_validate(row) for row in report_repo.get_inspection_issues(db)]

    logger.debug("GET /reports/inspection-issues returned %d row(s)", len(rows))
    return rows


@router.get(
    "/incomplete-lots",
    response_model=list[IncompleteLotRow],
    summary="Lots missing production, inspection, or shipping data",
    description=(
        "Returns all lots whose overall_completeness is below 100%, "
        "ordered most-incomplete first. Supports AC4 and AC10."
    ),
)
def incomplete_lots(db: Session = Depends(get_db)) -> list[IncompleteLotRow]:
    """
    Return all lots with missing data, ordered by completeness ascending.

    Returns:
        HTTP 200 with a JSON array of IncompleteLotRow objects.
        Empty array [] if all lots are fully complete.

    AC4:  Analyst can see which lots are missing data before a meeting.
    AC10: overall_completeness score visible per lot.
    """
    logger.info("GET /reports/incomplete-lots")

    rows = [IncompleteLotRow.model_validate(row) for row in report_repo.get_incomplete_lots(db)]

    logger.debug("GET /reports/incomplete-lots returned %d row(s)", len(rows))
    return rows


@router.get(
    "/line-issues",
    response_model=list[LineIssueRow],
    summary="Inspection issue counts and rates per production line",
    description=(
        "Returns total inspections, total issues, and issue rate percentage "
        "for each production line, ordered by total issues descending. "
        "Supports AC5."
    ),
)
def line_issues(db: Session = Depends(get_db)) -> list[LineIssueRow]:
    """
    Return inspection issue aggregates per production line.

    Returns:
        HTTP 200 with a JSON array of LineIssueRow objects (one per line).
        Empty array [] if no production or inspection records exist.

    AC5: Identify which production lines have the highest issue rates.
    """
    logger.info("GET /reports/line-issues")

    rows = [LineIssueRow.model_validate(row) for row in report_repo.get_line_issues(db)]

    logger.debug("GET /reports/line-issues returned %d row(s)", len(rows))
    return rows
