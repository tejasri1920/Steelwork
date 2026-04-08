# tests/integration/conftest.py
#
# Pytest fixtures for integration tests that run against a real PostgreSQL database.
#
# Unlike the SQLite unit tests in tests/conftest.py, these fixtures connect to the
# test PostgreSQL database specified in .env.test (TEST_DATABASE_URL).  This lets
# us verify:
#   - PostgreSQL-specific trigger logic (data_completeness auto-update)
#   - Real search_path=ops schema resolution
#   - Actual SQL dialect behaviour (dates, decimals, joins)
#
# Test isolation strategy:
#   - A session-scoped fixture seeds four lots with a "INT-" prefix into the real DB.
#   - Seed data is committed so all tests in the session can read it.
#   - A cleanup step deletes the test lots (CASCADE removes child records and
#     data_completeness rows) after the full session ends.
#   - Each test function gets a fresh SQLAlchemy session so sessions don't bleed
#     between tests.
#
# Skip behaviour:
#   If TEST_DATABASE_URL is not set in .env.test (or the environment), all
#   integration tests are skipped automatically — no PostgreSQL server needed for
#   the standard CI pipeline that uses SQLite.
#
# Prerequisites:
#   1. The "ops" schema must exist in the test database (run db/schema.sql).
#   2. All triggers must be installed.
#   3. The test database user must have INSERT / UPDATE / DELETE / SELECT on all
#      ops tables.

import os
from datetime import date
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ── Load .env.test ─────────────────────────────────────────────────────────────
# Resolve the project root (3 directories above this file):
#   backend/tests/integration/conftest.py  →  parents[3]  →  project root
_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_ROOT / ".env.test", override=False)

TEST_DB_URL: str = os.environ.get("TEST_DATABASE_URL", "")

# Render PostgreSQL URLs sometimes use the legacy "postgres://" scheme.
# SQLAlchemy 2.x requires "postgresql://".  Normalise it here.
if TEST_DB_URL.startswith("postgres://"):
    TEST_DB_URL = TEST_DB_URL.replace("postgres://", "postgresql://", 1)

# ── Skip entire module if TEST_DATABASE_URL is not configured ──────────────────
if not TEST_DB_URL:
    pytest.skip(
        "Skipping integration tests: TEST_DATABASE_URL is not set in .env.test",
        allow_module_level=True,
    )

# ── App imports (after env check so we don't fail on missing DATABASE_URL) ────
# The main conftest already set TESTING=true and DATABASE_URL=sqlite:///:memory:,
# so settings initialises fine.  We bypass settings entirely by creating our own
# engine directly from TEST_DATABASE_URL.
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.data_completeness import DataCompleteness  # noqa: E402
from app.models.inspection import InspectionRecord  # noqa: E402
from app.models.lot import Lot  # noqa: E402
from app.models.production import ProductionRecord  # noqa: E402
from app.models.shipping import ShippingRecord  # noqa: E402

# ── PostgreSQL engine (test database) ─────────────────────────────────────────
# We create a dedicated engine here rather than reusing the app's module-level
# engine (which points at SQLite in test mode).  search_path=ops tells PostgreSQL
# to resolve unqualified table names (e.g. "lots") inside the ops schema.
_pg_engine = create_engine(
    TEST_DB_URL,
    connect_args={"options": "-c search_path=ops"},
    # pool_pre_ping checks whether a connection is alive before using it.
    # Render's managed PostgreSQL can close idle connections.
    pool_pre_ping=True,
)
_PgSession = sessionmaker(autocommit=False, autoflush=False, bind=_pg_engine)

# ── Test lot identifiers ───────────────────────────────────────────────────────
# Prefix "INT-" clearly identifies rows inserted by integration tests.
# The cleanup fixture filters by these codes, so they never leak into production.
INT_LOT_A = "INT-A"
INT_LOT_B = "INT-B"
INT_LOT_C = "INT-C"
INT_LOT_D = "INT-D"
ALL_INT_CODES = [INT_LOT_A, INT_LOT_B, INT_LOT_C, INT_LOT_D]


# ── Session-scoped seed fixture ────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=False)
def pg_seed_db():
    """
    Seed four representative lots into the real PostgreSQL test database.

    Runs once for the entire integration test session (scope="session").
    Commits the rows so all subsequent test functions can read them via their
    own fresh sessions.

    PostgreSQL triggers automatically populate data_completeness after each
    child-record INSERT — this is one of the key behaviours being tested here
    (the SQLite unit tests replicate trigger logic manually in Python).

    Seed data mirrors the SQLite unit-test seed:
        INT-A  complete (prod + insp + ship)     → completeness = 100 (via trigger)
        INT-B  missing inspection                 → completeness = 67  (via trigger)
        INT-C  flagged inspection + On Hold ship  → completeness = 100 (via trigger)
        INT-D  no child records                   → completeness = 0   (via trigger)

    Teardown:
        Deletes the four test lots by lot_code after all session tests complete.
        ON DELETE CASCADE removes child records and data_completeness rows.

    Time complexity:  O(1) — fixed number of rows.
    Space complexity: O(1) — fixed number of ORM objects.
    """
    session: Session = _PgSession()

    try:
        # ── Pre-clean: remove stale rows from a previously interrupted test run ─
        # This guards against duplicate-key errors if tests were killed mid-run.
        _delete_test_lots(session)

        # ── Seed LOT headers ───────────────────────────────────────────────────
        lot_a = Lot(lot_code=INT_LOT_A, start_date=date(2026, 1, 10), end_date=date(2026, 1, 15))
        lot_b = Lot(lot_code=INT_LOT_B, start_date=date(2026, 1, 12), end_date=date(2026, 1, 18))
        lot_c = Lot(lot_code=INT_LOT_C, start_date=date(2026, 1, 20), end_date=date(2026, 1, 25))
        lot_d = Lot(lot_code=INT_LOT_D, start_date=date(2026, 2, 1), end_date=None)
        session.add_all([lot_a, lot_b, lot_c, lot_d])
        session.flush()  # Assigns lot_id values before inserting child records

        # ── INT-A: complete — prod + insp + ship ───────────────────────────────
        session.add(
            ProductionRecord(
                lot_id=lot_a.lot_id,
                production_date=date(2026, 1, 10),
                production_line="Line 2",
                quantity_produced=500,
                shift="Day",
                part_number="SW-8091-A",
                units_planned=500,
                downtime_min=0,
                line_issue=False,
            )
        )
        session.add(
            InspectionRecord(
                lot_id=lot_a.lot_id,
                inspection_date=date(2026, 1, 11),
                inspector_id="EMP-001",
                inspection_result="Pass",
                issue_flag=False,
                defect_count=0,
                sample_size=50,
            )
        )
        session.add(
            ShippingRecord(
                lot_id=lot_a.lot_id,
                ship_date=date(2026, 1, 15),
                carrier="FedEx Freight",
                destination="Detroit Assembly Plant",
                quantity_shipped=500,
                shipment_status="Delivered",
            )
        )

        # ── INT-B: missing inspection — completeness = 67 ──────────────────────
        session.add(
            ProductionRecord(
                lot_id=lot_b.lot_id,
                production_date=date(2026, 1, 12),
                production_line="Line 1",
                quantity_produced=300,
                shift="Night",
                part_number="SW-7020-B",
                units_planned=320,
                downtime_min=15,
                line_issue=False,
            )
        )
        # No InspectionRecord for INT-B → trigger sets has_inspection_data = false
        session.add(
            ShippingRecord(
                lot_id=lot_b.lot_id,
                ship_date=date(2026, 1, 18),
                carrier="UPS LTL",
                destination="Chicago Distribution Center",
                quantity_shipped=300,
                shipment_status="In Transit",
            )
        )

        # ── INT-C: flagged inspection + On Hold shipment ────────────────────────
        session.add(
            ProductionRecord(
                lot_id=lot_c.lot_id,
                production_date=date(2026, 1, 20),
                production_line="Line 3",
                quantity_produced=400,
                shift="Swing",
                part_number="SW-9100-C",
                units_planned=400,
                downtime_min=30,
                line_issue=True,
                primary_issue="Tool wear",
            )
        )
        session.add(
            InspectionRecord(
                lot_id=lot_c.lot_id,
                inspection_date=date(2026, 1, 21),
                inspector_id="EMP-042",
                inspection_result="Fail",
                issue_flag=True,
                issue_category="Dimensional",
                defect_count=12,
                sample_size=50,
            )
        )
        session.add(
            ShippingRecord(
                lot_id=lot_c.lot_id,
                ship_date=date(2026, 1, 25),
                carrier="FedEx Freight",
                destination="Cleveland Warehouse",
                quantity_shipped=400,
                shipment_status="On Hold",
            )
        )

        # ── INT-D: no child records — completeness = 0 ─────────────────────────
        # PostgreSQL trigger fires only on child-table inserts, so data_completeness
        # for INT-D will remain absent until a child row is inserted.
        # The API gracefully handles a missing data_completeness row (returns 0%).

        session.commit()  # Triggers run here; data_completeness rows are created
    except Exception:
        session.rollback()
        raise
    finally:
        # Do NOT close the session here — yield keeps it alive for teardown.
        pass

    # Yield a mapping of lot_code → lot_id so report tests can identify
    # which rows in the response belong to the seeded test lots.
    yield {
        INT_LOT_A: lot_a.lot_id,
        INT_LOT_B: lot_b.lot_id,
        INT_LOT_C: lot_c.lot_id,
        INT_LOT_D: lot_d.lot_id,
    }

    # ── Teardown ───────────────────────────────────────────────────────────────
    _delete_test_lots(session)
    session.close()  # Release the connection back to the pool


def _delete_test_lots(session: Session) -> None:
    """
    Remove all test lots and their child records from the database.

    The ORM foreign keys are ON DELETE RESTRICT (default), so child records
    must be deleted before the parent lot rows.  Order matters:
        1. production_records, inspection_records, shipping_records (children)
        2. data_completeness (child via FK from lots)
        3. lots (parent)

    Time complexity:  O(k) where k = number of test lots (constant = 4).
    Space complexity: O(1).
    """
    # Resolve the lot_ids for the test codes (may be empty on a fresh DB).
    lot_ids = [
        r[0]
        for r in session.query(Lot.lot_id).filter(Lot.lot_code.in_(ALL_INT_CODES)).all()
    ]
    if not lot_ids:
        return

    # Delete child rows first to avoid FK violation on lot deletion.
    session.query(ProductionRecord).filter(
        ProductionRecord.lot_id.in_(lot_ids)
    ).delete(synchronize_session=False)
    session.query(InspectionRecord).filter(
        InspectionRecord.lot_id.in_(lot_ids)
    ).delete(synchronize_session=False)
    session.query(ShippingRecord).filter(
        ShippingRecord.lot_id.in_(lot_ids)
    ).delete(synchronize_session=False)
    session.query(DataCompleteness).filter(
        DataCompleteness.lot_id.in_(lot_ids)
    ).delete(synchronize_session=False)
    session.query(Lot).filter(Lot.lot_id.in_(lot_ids)).delete(synchronize_session=False)
    session.commit()


# ── Per-test client fixture ────────────────────────────────────────────────────


@pytest.fixture()
def pg_client(pg_seed_db) -> TestClient:  # type: ignore[override]
    """
    FastAPI TestClient backed by a fresh PostgreSQL session.

    Depends on pg_seed_db to guarantee test data is present before each test.
    Each test gets its own session so read-only tests don't share state.

    Yields:
        TestClient: HTTP test client wired to the real PostgreSQL test database.
    """
    session: Session = _PgSession()
    # Override FastAPI's get_db dependency so route handlers use the test PG session
    # instead of the SQLite session set up by the main conftest.
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()  # Restore the default get_db dependency
        session.close()  # Release connection back to pool; prevents connection leaks
