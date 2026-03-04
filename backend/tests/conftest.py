# tests/conftest.py
#
# Pytest fixtures shared across all test files.
#
# Key design decisions:
#   1. SQLite in-memory database — no PostgreSQL needed to run tests.
#      Activated by setting TESTING=True in Settings (via env var or monkeypatching).
#      The _build_engine() function in database.py checks settings.is_testing and
#      returns `sqlite:///:memory:` instead of the PostgreSQL DATABASE_URL.
#
#   2. Isolated tables per test — each test function gets a fresh schema via the
#      `db` fixture (function scope). This prevents test pollution.
#
#   3. Four seed lots — LOT-A through LOT-D cover the key data scenarios:
#       LOT-A  complete data (prod + insp + ship) → completeness = 100
#       LOT-B  missing inspection                  → completeness = 67
#       LOT-C  flagged inspection + On Hold ship   → completeness = 100
#       LOT-D  no child records at all             → completeness = 0
#
#   4. refresh_data_completeness() called after seeding — replicates PostgreSQL
#      trigger logic for SQLite (triggers don't run in SQLite).
#
# AC → Fixture coverage:
#   AC1, AC2, AC7, AC8  → all four lots seeded (cross-function, summary views)
#   AC3                 → lots have different start_dates for date filtering
#   AC4, AC10           → LOT-B and LOT-D have completeness < 100
#   AC5                 → LOT-C has line_issue=True on production, issue_flag=True on inspection
#   AC6                 → LOT-C has flagged inspection + On Hold shipping record
#   AC9                 → LOT-A used for full detail drill-down

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set TESTING=true BEFORE importing app modules so _build_engine() picks it up.
# This must happen before any app import that triggers module-level engine creation.
os.environ["TESTING"] = "true"

# When running pytest from the backend/ directory, pydantic-settings can't find
# the .env file (which lives in the project root, one level up). DATABASE_URL is
# a required field in Settings, so without it Settings() raises a validation error.
# In test mode _build_engine() uses SQLite and never reads database_url, so any
# valid string works as a placeholder. setdefault leaves it unchanged if already set.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# ── Engine and session factory ────────────────────────────────────────────────

# SQLite in-memory database.
#
# Why StaticPool?
#   sqlite:///:memory: databases are per-connection — each new connection gets a
#   FRESH empty database. So if create_all() uses connection A and the session uses
#   connection B, the session sees no tables.
#   StaticPool forces all "connections" to share one underlying DBAPI connection,
#   so create_all() and the session both see the same in-memory database.
#
# check_same_thread=False: SQLite's default disallows sharing a connection across
# threads. We disable it because pytest may hand the session to a different thread.
SQLITE_URL = "sqlite:///:memory:"
_test_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # All sessions share one connection → same in-memory DB
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def db() -> Session:
    """
    Provide a clean SQLite in-memory database session for each test function.

    Lifecycle:
        1. Create all ORM-defined tables in the in-memory DB.
        2. Yield the session to the test.
        3. Drop all tables after the test completes (ensures isolation).

    The session is also registered as the FastAPI override so that the app's
    `get_db` dependency returns this test session instead of a PostgreSQL one.

    Scope: "function" — each test gets a fresh, empty database.
    """
    # Step 1: Create all tables (Lot, ProductionRecord, etc.) in the fresh in-memory DB.
    Base.metadata.create_all(_test_engine)

    # Step 2: Open a session bound to this test's engine.
    session = _TestingSessionLocal()

    # Step 3: Override FastAPI's get_db dependency so the app uses this test session
    # instead of opening a real PostgreSQL connection.
    # lambda: session — returns the same session object every time get_db is called.
    app.dependency_overrides[get_db] = lambda: session

    yield session  # Hand the session to the test function

    # Teardown (runs after the test finishes, even if the test raised an exception)
    session.close()  # Release the DB connection
    app.dependency_overrides.clear()  # Remove the test override
    Base.metadata.drop_all(_test_engine)  # Drop all tables → clean slate for the next test


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """
    Provide a FastAPI TestClient that uses the test database session.

    The `db` fixture (above) registers the test session override on the app.
    This fixture simply wraps the app in a TestClient for HTTP calls.

    Usage in tests:
        def test_something(client):
            response = client.get("/api/v1/lots/")
            assert response.status_code == 200

    Scope: "function" — each test gets a fresh client tied to its own DB.
    """
    # TestClient wraps the FastAPI app and lets us make HTTP requests in tests
    # without starting a real server. The db fixture has already registered the
    # test session override, so all requests use the in-memory SQLite DB.
    return TestClient(app)


@pytest.fixture(scope="function")
def seeded_db(db: Session) -> Session:
    """
    Seed the test database with four representative lots and call
    refresh_data_completeness() for each to simulate PostgreSQL triggers.

    Seed data:
        LOT-A  start_date=2026-01-10, end_date=2026-01-15
               Production: Line 2, 500 units, no issues
               Inspection: Pass, no flag
               Shipping:   Delivered to Detroit Assembly Plant
               Completeness: 100

        LOT-B  start_date=2026-01-12, end_date=2026-01-18
               Production: Line 1, 300 units, no issues
               Inspection: (none)
               Shipping:   In Transit
               Completeness: 67

        LOT-C  start_date=2026-01-20, end_date=2026-01-25
               Production: Line 3, 400 units, line_issue=True, primary_issue='Tool wear'
               Inspection: Fail, issue_flag=True, issue_category='Dimensional'
               Shipping:   On Hold
               Completeness: 100

        LOT-D  start_date=2026-02-01, end_date=None
               Production: (none)
               Inspection: (none)
               Shipping:   (none)
               Completeness: 0

    Returns the seeded db session so tests can add more rows if needed.

    AC3:  LOT-A/B in January, LOT-D in February → date filter tests
    AC4:  LOT-B (completeness=67) and LOT-D (completeness=0) are incomplete
    AC5:  LOT-C production has line_issue=True; LOT-C inspection has issue_flag=True
    AC6:  LOT-C inspection is flagged + shipping is On Hold
    AC10: Completeness scores: 100 (LOT-A), 67 (LOT-B), 100 (LOT-C), 0 (LOT-D)
    """
    raise NotImplementedError(
        "TODO: Create Lot, ProductionRecord, InspectionRecord, ShippingRecord objects "
        "for LOT-A, LOT-B, LOT-C, LOT-D. db.add_all(...). db.commit(). "
        "Call refresh_data_completeness(db, lot_id) for each lot. "
        "return db."
    )
