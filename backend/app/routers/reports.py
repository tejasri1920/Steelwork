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

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.reports import (
    IncompleteLotRow,
    InspectionIssueRow,
    LineIssueRow,
    LotSummaryRow,
)

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
        "Supports AC1, AC7, AC8, AC10."
    ),
)
def lot_summary(db: Session = Depends(get_db)) -> list[LotSummaryRow]:
    """
    Return the aggregated operational lot summary.

    Returns:
        HTTP 200 with a JSON array of LotSummaryRow objects.
        Empty array [] if no lots exist.

    AC1:  Shows all three data domains side-by-side for each lot.
    AC7:  One row per lot — clean format for meeting discussions.
    AC8:  latest_status column shows current shipment state.
    AC10: overall_completeness included in each row.
    """
    raise NotImplementedError("TODO: Call report_repo.get_lot_summary(db). Return the list.")


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
    raise NotImplementedError("TODO: Call report_repo.get_inspection_issues(db). Return the list.")


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
    raise NotImplementedError("TODO: Call report_repo.get_incomplete_lots(db). Return the list.")


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
    raise NotImplementedError("TODO: Call report_repo.get_line_issues(db). Return the list.")
