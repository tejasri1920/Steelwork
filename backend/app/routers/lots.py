# app/routers/lots.py
#
# FastAPI router for lot-related endpoints.
#
# Registered at prefix /api/v1 in main.py, so full paths are:
#   GET /api/v1/lots                  → list_lots()
#   GET /api/v1/lots/{lot_code}       → get_lot()
#
# AC coverage:
#   AC2  — retrieve a specific lot by lot_code
#   AC3  — filter lots by date range (start_date / end_date query params)
#   AC9  — return full lot detail (all child records)

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import lot_repo
from app.schemas.lot import LotDetail, LotSummary

# APIRouter groups related endpoints.
# prefix and tags are set here; main.py registers this router under /api/v1.
router = APIRouter(
    prefix="/lots",
    tags=["lots"],  # Groups endpoints under "lots" in the /docs Swagger UI
)


@router.get(
    "/",
    response_model=list[LotSummary],
    summary="List all lots (optionally filtered by date range)",
    description=(
        "Returns a list of lots with completeness scores. "
        "Supports AC3 date range filtering via start_date and end_date query params. "
        "Supports AC4 / AC10 because completeness scores are included in every row."
    ),
)
def list_lots(
    start_date: date | None = Query(
        default=None,
        description="Inclusive lower bound on lots.start_date (ISO-8601 date, e.g. 2026-01-01)",
    ),
    end_date: date | None = Query(
        default=None,
        description="Inclusive upper bound on lots.start_date (ISO-8601 date, e.g. 2026-01-31)",
    ),
    db: Session = Depends(get_db),  # FastAPI injects a DB session per request
) -> list[LotSummary]:
    """
    Return all lots, optionally filtered to a date range.

    Query parameters:
        start_date: Optional ISO-8601 date. Only lots whose start_date >= this value.
        end_date:   Optional ISO-8601 date. Only lots whose start_date <= this value.

    Returns:
        HTTP 200 with a JSON array of LotSummary objects.
        Empty array [] if no lots match the filter.

    AC3: Date range filtering.
    AC4/AC10: overall_completeness and has_*_data flags are included in each row.
    """
    lots = lot_repo.get_lots(db, start_date, end_date)

    # Flatten Lot + its data_completeness into a LotSummary for each row.
    # data_completeness is a related object (one-to-one), so we access it as an attribute.
    # It can be None if the lot was just created and the trigger hasn't run yet.
    result = []
    for lot in lots:
        dc = lot.data_completeness  # DataCompleteness ORM object, or None
        result.append(
            LotSummary(
                lot_id=lot.lot_id,
                lot_code=lot.lot_code,
                start_date=lot.start_date,
                end_date=lot.end_date,
                has_production_data=dc.has_production_data if dc else False,
                has_inspection_data=dc.has_inspection_data if dc else False,
                has_shipping_data=dc.has_shipping_data if dc else False,
                overall_completeness=Decimal(str(dc.overall_completeness)) if dc else Decimal(0),
            )
        )
    return result


@router.get(
    "/{lot_code}",
    response_model=LotDetail,
    summary="Get full detail for a single lot by its lot_code",
    description=(
        "Returns the lot header plus all production, inspection, and shipping records "
        "for the given lot_code. Returns 404 if the lot does not exist. "
        "Supports AC2 (specific lot retrieval) and AC9 (full detail view)."
    ),
)
def get_lot(
    lot_code: str,  # Path parameter — extracted from the URL
    db: Session = Depends(get_db),
) -> LotDetail:
    """
    Return full details for a single lot identified by lot_code.

    Path parameter:
        lot_code: Human-readable lot identifier, e.g. 'LOT-20260112-001'.

    Returns:
        HTTP 200 with a LotDetail JSON object (includes all child records).
        HTTP 404 if no lot with this lot_code exists.

    AC2: Retrieve a specific lot by lot_code.
    AC9: Full drill-down including production, inspection, and shipping records.
    """
    raise NotImplementedError(
        "TODO: Call lot_repo.get_lot_by_code(db, lot_code). "
        "If None, raise HTTPException(status_code=404, detail='Lot not found'). "
        "Flatten lot + data_completeness into LotDetail dict. Return it."
    )
