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
#
# Logging:
#   INFO   — each request with its filter parameters
#   DEBUG  — result counts returned to the caller
#   WARNING — 404 responses (lot_code not found in the database)

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import lot_repo
from app.schemas.lot import LotDetail, LotSummary

# Module-level logger.  Name follows __name__ convention: "app.routers.lots".
# All records propagate to the root logger, which routes them to the configured
# handlers (console at WARNING+, file at DEBUG+).
logger = logging.getLogger(__name__)

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
    logger.info(
        "GET /lots/ | start_date=%s end_date=%s",
        start_date,
        end_date,
    )

    lots = lot_repo.get_lots(db, start_date, end_date)

    logger.debug("GET /lots/ returned %d lot(s)", len(lots))

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
    logger.info("GET /lots/%s", lot_code)

    lot = lot_repo.get_lot_by_code(db, lot_code)
    if lot is None:
        # WARNING not ERROR: a missing lot is a client error (bad lot_code), not a
        # server fault.  WARNING makes it easy to spot bad requests in the log file.
        logger.warning("GET /lots/%s → 404 not found", lot_code)
        # Return 404 rather than 500 so the frontend can show a "Not found" page (AC2).
        raise HTTPException(status_code=404, detail="Lot not found")

    logger.debug(
        "GET /lots/%s → found lot_id=%d | prod=%d insp=%d ship=%d",
        lot_code,
        lot.lot_id,
        len(lot.production_records),
        len(lot.inspection_records),
        len(lot.shipping_records),
    )

    dc = lot.data_completeness  # DataCompleteness ORM object, or None
    return LotDetail(
        lot_id=lot.lot_id,
        lot_code=lot.lot_code,
        start_date=lot.start_date,
        end_date=lot.end_date,
        # Pass ORM list objects directly — Pydantic's from_attributes=True serialises them.
        production_records=lot.production_records,
        inspection_records=lot.inspection_records,
        shipping_records=lot.shipping_records,
        has_production_data=dc.has_production_data if dc else False,
        has_inspection_data=dc.has_inspection_data if dc else False,
        has_shipping_data=dc.has_shipping_data if dc else False,
        overall_completeness=Decimal(str(dc.overall_completeness)) if dc else Decimal(0),
        created_at=lot.created_at,
        updated_at=lot.updated_at,
    )
