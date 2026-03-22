# app/repositories/report_repo.py
#
# Database access functions for the four analytical report endpoints.
#
# Each function mirrors one PostgreSQL view. Because SQLite (used in tests) does
# not support views, GROUP_CONCAT, or BOOL_OR, all aggregations are performed in
# Python after fetching the raw rows via the ORM. This approach is correct and
# efficient for the data volumes expected here (hundreds of lots, not millions).
#
# Views and their AC coverage:
#   v_lot_summary                → get_lot_summary()      AC1, AC2, AC7, AC8
#   v_inspection_issue_shipping  → get_inspection_issues() AC5, AC6
#   v_incomplete_lots            → get_incomplete_lots()   AC4, AC10
#   v_issues_by_production_line  → get_line_issues()       AC5
#
# All functions return plain Python dicts (not ORM objects) because these queries
# aggregate across multiple tables — there is no single ORM class to return.
# The router validates the dicts against Pydantic report schemas.

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.data_completeness import DataCompleteness
from app.models.inspection import InspectionRecord
from app.models.lot import Lot
from app.models.production import ProductionRecord
from app.models.shipping import ShippingRecord


def get_lot_summary(db: Session) -> list[dict]:
    """
    Return one aggregated row per lot: total production, any issues, latest shipment.

    This is the primary view for meeting discussions (AC7). It mirrors v_lot_summary:
        SELECT
            l.lot_id, l.start_date, l.end_date,
            SUM(p.quantity_produced)             AS total_produced,
            STRING_AGG(DISTINCT p.production_line, ', ') AS lines_used,
            BOOL_OR(i.issue_flag)                AS any_issues,
            COUNT(*) FILTER (WHERE i.issue_flag) AS issue_count,
            MAX(s.shipment_status)               AS latest_status,
            c.overall_completeness
        FROM lots l
        LEFT JOIN production_records p ON l.lot_id = p.lot_id
        LEFT JOIN inspection_records i ON l.lot_id = i.lot_id
        LEFT JOIN shipping_records   s ON l.lot_id = s.lot_id
        JOIN  data_completeness      c ON l.lot_id = c.lot_id
        GROUP BY l.lot_id, l.start_date, l.end_date, c.overall_completeness
        ORDER BY l.lot_id

    Implementation note:
        Rather than fighting SQLite's dialect differences (no BOOL_OR, no FILTER),
        we load all child records via joinedload and aggregate in Python.
        O(N) time and space where N = number of lots, with a constant JOIN factor.

    Args:
        db: SQLAlchemy session.

    Returns:
        List of dicts, one per lot. Keys match LotSummaryRow schema fields.
        Empty list if no lots exist.

    Time complexity:  O(N) where N = number of lots.
    Space complexity: O(N).
    """
    # Single query with four joinedloads — one SQL trip, no N+1 queries.
    lots = (
        db.query(Lot)
        .options(
            joinedload(Lot.production_records),
            joinedload(Lot.inspection_records),
            joinedload(Lot.shipping_records),
            joinedload(Lot.data_completeness),
        )
        .order_by(Lot.lot_id)
        .all()
    )

    result = []
    for lot in lots:
        prods = lot.production_records    # List[ProductionRecord] (may be empty)
        insps = lot.inspection_records    # List[InspectionRecord]  (may be empty)
        ships = lot.shipping_records      # List[ShippingRecord]    (may be empty)
        dc = lot.data_completeness        # DataCompleteness | None

        # ── Aggregate production columns ────────────────────────────────────
        # None when there are no production records (mirrors SQL LEFT JOIN + SUM/AGG
        # returning NULL when all joined rows are NULL).
        total_produced: int | None = sum(p.quantity_produced for p in prods) if prods else None
        lines_used: str | None = (
            ", ".join(sorted(set(p.production_line for p in prods))) if prods else None
        )

        # ── Aggregate inspection columns ────────────────────────────────────
        # any_issues: True if ≥1 inspection has issue_flag=True; False if ≥1 inspection
        # exists but none flagged; None if there are no inspection records at all.
        # This mirrors PostgreSQL's BOOL_OR aggregate (returns NULL for empty groups).
        any_issues: bool | None = any(i.issue_flag for i in insps) if insps else None
        issue_count: int | None = sum(1 for i in insps if i.issue_flag) if insps else None

        # ── Aggregate shipping columns ──────────────────────────────────────
        # MAX(shipment_status) lexicographically — consistent with the PostgreSQL view.
        latest_status: str | None = max((s.shipment_status for s in ships), default=None) if ships else None

        result.append(
            {
                "lot_id": lot.lot_id,
                "start_date": lot.start_date,
                "end_date": lot.end_date,
                "total_produced": total_produced,
                "lines_used": lines_used,
                "any_issues": any_issues,
                "issue_count": issue_count,
                "latest_status": latest_status,
                # Fallback to 0 if no data_completeness row exists (shouldn't happen
                # in production, but guards against the fixture not yet calling refresh).
                "overall_completeness": dc.overall_completeness if dc else Decimal("0"),
            }
        )

    return result


def get_inspection_issues(db: Session) -> list[dict]:
    """
    Return all lots with at least one inspection issue, with their shipment status.

    Mirrors v_inspection_issue_shipping:
        SELECT
            l.lot_id,
            i.inspection_result,
            i.issue_flag,
            s.shipment_status,
            s.ship_date,
            s.destination
        FROM lots l
        JOIN  inspection_records i ON l.lot_id = i.lot_id
        LEFT JOIN shipping_records s ON l.lot_id = s.lot_id
        WHERE i.issue_flag = TRUE
        ORDER BY l.lot_id, s.ship_date

    LEFT JOIN on shipping makes gaps visible: flagged lots with no shipment record
    still appear with NULL shipment columns (AC6 requirement).

    Args:
        db: SQLAlchemy session.

    Returns:
        List of dicts with keys matching InspectionIssueRow schema fields.
        Empty list if no flagged inspection records exist.

    Time complexity:  O(F) where F = number of flagged inspection records.
    Space complexity: O(F).
    """
    # outerjoin: InspectionRecord LEFT JOIN ShippingRecord on lot_id.
    # Rows where no shipping record exists return (InspectionRecord, None).
    rows = (
        db.query(InspectionRecord, ShippingRecord)
        .outerjoin(ShippingRecord, InspectionRecord.lot_id == ShippingRecord.lot_id)
        .filter(InspectionRecord.issue_flag == True)  # noqa: E712 — SQLAlchemy needs ==
        .order_by(InspectionRecord.lot_id, ShippingRecord.ship_date)
        .all()
    )

    result = []
    for insp, ship in rows:
        result.append(
            {
                "lot_id": insp.lot_id,
                "inspection_result": insp.inspection_result,
                "issue_flag": insp.issue_flag,
                # ship is None when no ShippingRecord row matched (LEFT JOIN null).
                "shipment_status": ship.shipment_status if ship else None,
                "ship_date": ship.ship_date if ship else None,
                "destination": ship.destination if ship else None,
            }
        )

    return result


def get_incomplete_lots(db: Session) -> list[dict]:
    """
    Return all lots whose overall_completeness < 100, ordered most-incomplete first.

    Mirrors v_incomplete_lots:
        SELECT
            l.lot_id, l.start_date, l.end_date,
            c.has_production_data,
            c.has_inspection_data,
            c.has_shipping_data,
            c.overall_completeness
        FROM lots l
        JOIN data_completeness c ON l.lot_id = c.lot_id
        WHERE c.overall_completeness < 100
        ORDER BY c.overall_completeness ASC

    Supports AC4 (surface missing data) and AC10 (completeness score visible).

    Args:
        db: SQLAlchemy session.

    Returns:
        List of dicts with keys matching IncompleteLotRow schema fields.
        Empty list if all lots are 100% complete.

    Time complexity:  O(I) where I = number of incomplete lots.
    Space complexity: O(I).
    """
    # INNER JOIN: only lots that have a data_completeness row are returned.
    # lots without a row (shouldn't happen after seeding) are silently excluded.
    rows = (
        db.query(Lot, DataCompleteness)
        .join(DataCompleteness, Lot.lot_id == DataCompleteness.lot_id)
        .filter(DataCompleteness.overall_completeness < 100)
        .order_by(DataCompleteness.overall_completeness.asc())  # most-incomplete first
        .all()
    )

    result = []
    for lot, dc in rows:
        result.append(
            {
                "lot_id": lot.lot_id,
                "start_date": lot.start_date,
                "end_date": lot.end_date,
                "has_production_data": dc.has_production_data,
                "has_inspection_data": dc.has_inspection_data,
                "has_shipping_data": dc.has_shipping_data,
                "overall_completeness": dc.overall_completeness,
            }
        )

    return result


def get_line_issues(db: Session) -> list[dict]:
    """
    Return issue counts and rates aggregated per production line.

    Mirrors v_issues_by_production_line:
        SELECT
            p.production_line,
            COUNT(*)                                                    AS total_inspections,
            SUM(CASE WHEN i.issue_flag THEN 1 ELSE 0 END)             AS total_issues,
            ROUND(
                SUM(CASE WHEN i.issue_flag THEN 1 ELSE 0 END) * 100.0
                / NULLIF(COUNT(*), 0), 1
            )                                                           AS issue_rate_pct
        FROM production_records p
        JOIN inspection_records i ON p.lot_id = i.lot_id
        GROUP BY p.production_line
        ORDER BY total_issues DESC

    INNER JOIN: only lots that have BOTH production and inspection records appear.
    This is intentional — a production run without any inspection cannot contribute
    to an issue rate.

    Args:
        db: SQLAlchemy session.

    Returns:
        List of dicts with keys matching LineIssueRow schema fields.
        Empty list if no production or inspection records exist.

    Time complexity:  O(P + I) where P, I = production and inspection record counts.
    Space complexity: O(L) where L = number of distinct production lines (≤4).
    """
    # INNER JOIN on lot_id: pairs each production record with every inspection record
    # for the same lot. This is equivalent to the PostgreSQL view's JOIN clause.
    rows = (
        db.query(ProductionRecord, InspectionRecord)
        .join(InspectionRecord, ProductionRecord.lot_id == InspectionRecord.lot_id)
        .all()
    )

    if not rows:
        return []  # Empty DB: no rows to aggregate — O(1) early exit

    # Aggregate in Python by production_line.
    # defaultdict avoids a key-existence check on every iteration.
    # Time: O(R) where R = number of (prod, insp) pairs.
    line_stats: dict[str, dict] = defaultdict(
        lambda: {"total_inspections": 0, "total_issues": 0}
    )

    for prod, insp in rows:
        line = prod.production_line
        line_stats[line]["total_inspections"] += 1
        if insp.issue_flag:
            line_stats[line]["total_issues"] += 1

    # Build result list and calculate rate.
    result = []
    for line, stats in line_stats.items():
        total = stats["total_inspections"]
        issues = stats["total_issues"]
        # NULLIF(COUNT(*), 0) guard — total is always ≥1 here, but explicit is safer.
        rate = Decimal(str(round(issues * 100.0 / total, 1))) if total > 0 else Decimal("0.0")
        result.append(
            {
                "production_line": line,
                "total_inspections": total,
                "total_issues": issues,
                "issue_rate_pct": rate,
            }
        )

    # ORDER BY total_issues DESC — mirrors the PostgreSQL view's ORDER BY clause.
    result.sort(key=lambda x: x["total_issues"], reverse=True)
    return result
