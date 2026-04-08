# app/repositories/lot_repo.py
#
# Database access functions for the `lots` table and its child records.
#
# Supports:
#   AC2  — look up a specific lot by its human-readable lot_code
#   AC3  — filter all lots by production date range
#   AC4  — surface lots with missing data (via data_completeness)
#   AC9  — return full lot detail including all child records
#
# Design notes:
#   - All functions accept a SQLAlchemy `Session` as their first argument.
#     This enables dependency injection (real DB in production, test DB in tests).
#   - Functions return ORM objects. Pydantic serialization happens in the router layer.
#   - Eager loading (.options(joinedload(...))) is used to avoid N+1 query problems
#     when accessing child relationships.

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.data_completeness import DataCompleteness
from app.models.inspection import InspectionRecord
from app.models.lot import Lot
from app.models.production import ProductionRecord
from app.models.shipping import ShippingRecord

# Module-level logger.  Name follows __name__ convention: "app.repositories.lot_repo".
logger = logging.getLogger(__name__)


def get_lots(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Lot]:
    """
    Return all lots, optionally filtered to those whose start_date falls within
    [start_date, end_date] (inclusive on both ends).

    This implements AC3: date range filtering.
    Anchors on lots.start_date so incomplete lots (missing child records) still appear
    with NULL child data — gaps are visible rather than silently excluded.

    Also eagerly loads data_completeness for each lot so the caller can read
    completeness scores without triggering additional queries (avoids N+1).

    Args:
        db:         SQLAlchemy session (injected by FastAPI via get_db dependency).
        start_date: Optional lower bound (inclusive). No lower limit if None.
        end_date:   Optional upper bound (inclusive). No upper limit if None.

    Returns:
        List of Lot ORM objects with data_completeness relationship loaded.
        Empty list if no lots match the filter.

    Time complexity:  O(N) where N = number of lots in the date range.
    Space complexity: O(N) — all matching lots held in memory.
    """
    # joinedload eagerly fetches the related data_completeness row in the same SQL query
    # (a LEFT OUTER JOIN), so accessing lot.data_completeness later never fires extra queries.
    query = db.query(Lot).options(joinedload(Lot.data_completeness))

    if start_date is not None:
        query = query.filter(Lot.start_date >= start_date)
    if end_date is not None:
        query = query.filter(Lot.start_date <= end_date)

    results = query.order_by(Lot.lot_id).all()
    logger.debug(
        "get_lots(start_date=%s, end_date=%s) → %d lot(s)",
        start_date,
        end_date,
        len(results),
    )
    return results


def get_lot_by_code(db: Session, lot_code: str) -> Lot | None:
    """
    Return a single lot by its human-readable lot_code (e.g. 'LOT-20260112-001').

    Eagerly loads ALL child relationships (production_records, inspection_records,
    shipping_records, data_completeness) because the lot detail endpoint (AC9) needs
    all of them in one response. Using joinedload prevents N+1 SELECT statements.

    Args:
        db:       SQLAlchemy session.
        lot_code: Human-readable lot identifier string.

    Returns:
        Lot ORM object with all relationships loaded, or None if not found.
        The router translates None → HTTP 404.

    Time complexity:  O(P + I + S) where P, I, S are counts of child records.
    Space complexity: O(P + I + S) — all child records held in memory.
    """
    # joinedload fetches all four relationships in the same query using LEFT OUTER JOINs,
    # avoiding N+1 queries when the router accesses lot.production_records etc.
    result = (
        db.query(Lot)
        .options(
            joinedload(Lot.production_records),  # AC9: production detail
            joinedload(Lot.inspection_records),  # AC9: inspection detail
            joinedload(Lot.shipping_records),  # AC9: shipping detail
            joinedload(Lot.data_completeness),  # AC4/AC10: completeness score
        )
        .filter(Lot.lot_code == lot_code)
        .first()  # Returns None if the lot_code doesn't exist → router raises 404
    )
    if result is None:
        logger.debug("get_lot_by_code(%r) → not found", lot_code)
    else:
        logger.debug("get_lot_by_code(%r) → lot_id=%d", lot_code, result.lot_id)
    return result


def refresh_data_completeness(db: Session, lot_id: int) -> None:
    """
    Recalculate and upsert the data_completeness row for a given lot.

    In production (PostgreSQL), this is done automatically by DB triggers.
    This function exists ONLY for the test environment (SQLite), where triggers
    don't run, so tests must call this manually after seeding data.

    Completeness score formula (mirrors the PostgreSQL trigger logic):
        has_prod  = EXISTS(SELECT 1 FROM production_records WHERE lot_id = ?)
        has_insp  = EXISTS(SELECT 1 FROM inspection_records  WHERE lot_id = ?)
        has_ship  = EXISTS(SELECT 1 FROM shipping_records    WHERE lot_id = ?)
        score     = ROUND((has_prod + has_insp + has_ship) / 3.0 * 100)
        → Possible values: 0, 33, 67, 100

    Args:
        db:     SQLAlchemy session.
        lot_id: The lot to recalculate completeness for.

    Returns:
        None. Commits the upserted DataCompleteness row to the session.

    Time complexity:  O(1) — three EXISTS subqueries, one upsert.
    Space complexity: O(1) — only one DataCompleteness row touched.
    """
    # Three EXISTS-style checks — one per data domain.
    # .first() returns the object if ≥1 row exists, or None if no rows → bool.
    has_prod = (
        db.query(ProductionRecord).filter(ProductionRecord.lot_id == lot_id).first() is not None
    )
    has_insp = (
        db.query(InspectionRecord).filter(InspectionRecord.lot_id == lot_id).first() is not None
    )
    has_ship = db.query(ShippingRecord).filter(ShippingRecord.lot_id == lot_id).first() is not None

    # Mirror the PostgreSQL trigger formula: ROUND((prod+insp+ship) / 3.0 * 100)
    # Possible results: 0 (none), 33 (one), 67 (two), 100 (all three).
    score = round((int(has_prod) + int(has_insp) + int(has_ship)) / 3.0 * 100)

    # Upsert the DataCompleteness row for this lot.
    dc = db.query(DataCompleteness).filter(DataCompleteness.lot_id == lot_id).first()
    if dc is None:
        # First time seeding this lot — create a new row.
        dc = DataCompleteness(
            lot_id=lot_id,
            has_production_data=has_prod,
            has_inspection_data=has_insp,
            has_shipping_data=has_ship,
            overall_completeness=Decimal(str(score)),
        )
        db.add(dc)
    else:
        # Update the existing row in-place.
        # mypy sees Column[bool]/Column[Decimal] on the left-hand side, but the
        # SQLAlchemy mypy plugin maps ORM attribute assignment to the underlying
        # Python type at runtime. The assignments are correct; suppress with inline ignore.
        dc.has_production_data = has_prod  # type: ignore[assignment]
        dc.has_inspection_data = has_insp  # type: ignore[assignment]
        dc.has_shipping_data = has_ship  # type: ignore[assignment]
        dc.overall_completeness = Decimal(str(score))  # type: ignore[assignment]

    db.commit()  # Flush to the in-memory SQLite DB; connection is not closed here.
