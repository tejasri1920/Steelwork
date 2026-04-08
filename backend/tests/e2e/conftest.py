# tests/e2e/conftest.py
#
# Pytest fixtures that start the backend and frontend servers for
# end-to-end (Playwright) tests, and seed the test database with known data.
#
# Fixture lifecycle (session-scoped):
#   1. e2e_seed_db     — seeds four INT-* lots directly into PostgreSQL via
#                        SQLAlchemy so the frontend can display real data.
#   2. backend_server  — starts uvicorn on port 8001 with TEST_DATABASE_URL.
#   3. frontend_server — builds the React app (`npm run build`) then serves
#                        it via `vite preview` on port 5174.  Using preview
#                        (pre-compiled static files) rather than `vite dev`
#                        avoids the multi-minute first-request compilation that
#                        caused Playwright tests to hang indefinitely.
#   4. base_url        — overrides pytest-playwright's base_url fixture so
#                        page.goto("/") resolves to http://127.0.0.1:5174.
#
# Skip behaviour:
#   If TEST_DATABASE_URL is not set in .env.test, all e2e tests are skipped
#   automatically (same as the integration tests).
#
# Prerequisites:
#   - TEST_DATABASE_URL in .env.test pointing at a real PostgreSQL database
#     (ops schema must exist with tables and triggers — run setup_db.py once).
#   - Node.js installed (npm available on PATH).
#   - Playwright browser binaries installed:
#       poetry run playwright install
#   - All frontend npm deps installed:
#       cd frontend && npm install

import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ── Resolve paths ──────────────────────────────────────────────────────────────
# backend/tests/e2e/conftest.py  → parents[3] → project root
_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_DIR = _ROOT / "backend"
_FRONTEND_DIR = _ROOT / "frontend"

# ── Load .env.test ─────────────────────────────────────────────────────────────
load_dotenv(_ROOT / ".env.test", override=False)

TEST_DB_URL: str = os.environ.get("TEST_DATABASE_URL", "")
if TEST_DB_URL.startswith("postgres://"):
    TEST_DB_URL = TEST_DB_URL.replace("postgres://", "postgresql://", 1)

# Skip this entire module if TEST_DATABASE_URL is not configured.
if not TEST_DB_URL:
    pytest.skip(
        "Skipping e2e tests: TEST_DATABASE_URL is not set in .env.test",
        allow_module_level=True,
    )

# ── App model imports (safe after skip guard above) ────────────────────────────
# sys.path must include the backend/ dir so the ORM models can be imported.
sys.path.insert(0, str(_BACKEND_DIR))
from app.models.data_completeness import DataCompleteness  # noqa: E402
from app.models.inspection import InspectionRecord  # noqa: E402
from app.models.lot import Lot  # noqa: E402
from app.models.production import ProductionRecord  # noqa: E402
from app.models.shipping import ShippingRecord  # noqa: E402

# ── PostgreSQL engine (test database) ─────────────────────────────────────────
_pg_engine = create_engine(
    TEST_DB_URL,
    connect_args={"options": "-c search_path=ops"},
    pool_pre_ping=True,
)
_PgSession = sessionmaker(autocommit=False, autoflush=False, bind=_pg_engine)

# ── Port assignments ───────────────────────────────────────────────────────────
# Use non-standard ports so e2e tests don't collide with running dev servers.
_BACKEND_PORT = 8001
_FRONTEND_PORT = 5174

# ── Lot codes seeded by these tests ───────────────────────────────────────────
# "INT-" prefix clearly identifies rows inserted by these tests so they can
# be reliably cleaned up without accidentally touching production data.
_E2E_LOT_CODES = ["INT-A", "INT-B", "INT-C", "INT-D"]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _wait_for(url: str, timeout_s: float = 30.0) -> None:
    """
    Poll a URL until it returns any response or the timeout expires.

    Used to wait for uvicorn/vite to finish starting up before tests run.

    Args:
        url:       URL to poll (e.g. "http://localhost:8001/health").
        timeout_s: Maximum seconds to wait before raising TimeoutError.

    Raises:
        TimeoutError: If the server does not respond within timeout_s seconds.

    Time complexity:  O(timeout_s / 0.5) — polls every 500 ms.
    Space complexity: O(1).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            httpx.get(url, timeout=2.0)
            return  # Server responded — ready
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Server at {url} did not start within {timeout_s}s")


def _free_port(port: int) -> None:
    """
    Kill any process that is currently listening on a TCP port.

    Called before starting backend/frontend servers to prevent "address already
    in use" errors from zombie processes left by a previously interrupted test run.

    On Windows:  parses `netstat -ano` to find the PID, then calls taskkill.
    On non-Windows: this is a no-op (Unix typically recycles ports faster).

    Args:
        port: TCP port number to free (e.g. 8001 or 5174).

    Time complexity:  O(L) where L = number of lines in netstat output (hundreds).
    Space complexity: O(L).
    """
    if sys.platform != "win32":
        return
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in result.stdout.splitlines():
            # Match lines like "TCP  127.0.0.1:8001  ...  LISTENING  26664"
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1] if parts else ""
                if pid and pid != "0":
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True,
                        timeout=5,
                    )
    except Exception:
        pass  # Best-effort: if we can't free the port, the Popen will fail with a clear error


def _kill(proc: "subprocess.Popen[bytes]") -> None:
    """
    Terminate a subprocess and wait for it to exit.

    On Windows, terminate() sends CTRL+BREAK which may leave child processes
    (e.g. the Node.js process spawned by npm) running.  We follow up with
    kill() after a short grace period to ensure cleanup.

    Args:
        proc: The subprocess.Popen instance to stop.

    Time complexity:  O(1).
    Space complexity: O(1).
    """
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _delete_e2e_lots(session: Session) -> None:
    """
    Remove all INT-* e2e test lots and their child records from the database.

    Foreign keys use ON DELETE RESTRICT (ORM default), so child rows must be
    removed before the parent lots row or PostgreSQL will raise a FK violation.

    Deletion order:
        1. production_records   (child)
        2. inspection_records   (child)
        3. shipping_records     (child)
        4. data_completeness    (child via FK from lots)
        5. lots                 (parent)

    Args:
        session: An open SQLAlchemy Session connected to the test database.

    Time complexity:  O(k) where k = number of test lots (constant = 4).
    Space complexity: O(1).
    """
    lot_ids = [
        r[0] for r in session.query(Lot.lot_id).filter(Lot.lot_code.in_(_E2E_LOT_CODES)).all()
    ]
    if not lot_ids:
        return

    session.query(ProductionRecord).filter(ProductionRecord.lot_id.in_(lot_ids)).delete(
        synchronize_session=False
    )
    session.query(InspectionRecord).filter(InspectionRecord.lot_id.in_(lot_ids)).delete(
        synchronize_session=False
    )
    session.query(ShippingRecord).filter(ShippingRecord.lot_id.in_(lot_ids)).delete(
        synchronize_session=False
    )
    session.query(DataCompleteness).filter(DataCompleteness.lot_id.in_(lot_ids)).delete(
        synchronize_session=False
    )
    session.query(Lot).filter(Lot.lot_id.in_(lot_ids)).delete(synchronize_session=False)
    session.commit()


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def e2e_seed_db():
    """
    Seed four representative lots into the real PostgreSQL test database.

    Called once per test session (scope="session", autouse=True).  Rows are
    committed so the uvicorn backend process (a separate subprocess) can read
    them when the Playwright browser makes API requests.

    Pre-clean step removes any stale rows left by a previously interrupted run
    so we never hit duplicate-key errors.

    Seed data:
        INT-A  complete (prod + insp + ship)       completeness = 100
        INT-B  missing inspection                   completeness = 67
        INT-C  flagged inspection + On Hold ship    completeness = 100
        INT-D  no child records                     completeness = 0

    Teardown:
        Deletes the four lots by lot_code (CASCADE removes children).

    Time complexity:  O(1) — fixed number of rows.
    Space complexity: O(1) — fixed number of ORM objects in memory.
    """
    session: Session = _PgSession()
    try:
        # Remove stale rows from a previously interrupted test run.
        _delete_e2e_lots(session)

        # ── Lot headers ────────────────────────────────────────────────────────
        lot_a = Lot(lot_code="INT-A", start_date=date(2026, 1, 10), end_date=date(2026, 1, 15))
        lot_b = Lot(lot_code="INT-B", start_date=date(2026, 1, 12), end_date=date(2026, 1, 18))
        lot_c = Lot(lot_code="INT-C", start_date=date(2026, 1, 20), end_date=date(2026, 1, 25))
        lot_d = Lot(lot_code="INT-D", start_date=date(2026, 2, 1), end_date=None)
        session.add_all([lot_a, lot_b, lot_c, lot_d])
        session.flush()  # Assign lot_id values before inserting child records

        # ── INT-A: complete ────────────────────────────────────────────────────
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

        # ── INT-B: missing inspection ──────────────────────────────────────────
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

        # ── INT-C: flagged inspection + On Hold shipment ───────────────────────
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
        # for INT-D remains absent until a child row is inserted.

        session.commit()  # Triggers run here; data_completeness rows are created
    except Exception:
        session.rollback()
        raise
    finally:
        pass  # Keep session alive for teardown below

    yield  # E2E tests run here

    # ── Teardown ───────────────────────────────────────────────────────────────
    _delete_e2e_lots(session)
    session.close()  # Release connection back to the pool


@pytest.fixture(scope="session")
def backend_server(e2e_seed_db):
    """
    Start the FastAPI backend on port 8001 using the test PostgreSQL database.

    Depends on e2e_seed_db to guarantee INT-* lots are committed before the
    backend process starts (the backend reads committed rows only).

    Environment:
        DATABASE_URL    — set to TEST_DATABASE_URL so the backend reads from
                          the test database, not the production one.
        TESTING         — set to "false" so _build_engine() uses PostgreSQL.
        ALLOWED_ORIGINS — includes the frontend test port (5174).

    The backend process is killed automatically when the test session ends.

    Scope: "session" — one backend instance shared across all e2e tests.

    Time complexity:  O(1).
    Space complexity: O(1).
    """
    env = {
        **os.environ,
        "DATABASE_URL": TEST_DB_URL,
        "TESTING": "false",
        "ALLOWED_ORIGINS": (
            f"http://localhost:{_FRONTEND_PORT},http://localhost:3000,http://localhost:5173"
        ),
        "LOG_LEVEL": "warning",  # Suppress INFO noise during tests
    }
    # Kill any zombie process from a previous interrupted test run that may still
    # be holding the backend port.  Without this, the new uvicorn would fail to
    # bind and _wait_for would succeed against the OLD process (wrong code).
    _free_port(_BACKEND_PORT)

    # Start uvicorn.  Use the same Python executable that runs pytest so we pick
    # up the correct virtual-environment packages.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(_BACKEND_PORT),
        ],
        cwd=str(_BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,  # Suppress uvicorn access logs in test output
        stderr=subprocess.PIPE,
    )

    try:
        _wait_for(f"http://127.0.0.1:{_BACKEND_PORT}/health")
    except TimeoutError:
        # Kill before reading stderr to avoid deadlock (see frontend_server for details).
        _kill(proc)
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        pytest.fail(f"Backend server did not start on port {_BACKEND_PORT}.\nStderr: {stderr}")

    # ── Warm up the database connection pool ──────────────────────────────────
    # Render's free-tier PostgreSQL can take 20–60 s to serve the first query
    # when the connection pool is cold.  We make one blocking API call with a
    # long timeout here so the pool is fully warm before Playwright starts
    # navigating, preventing individual test assertions from timing out.
    #
    # We use httpx directly (not _wait_for) because _wait_for uses a 2-second
    # per-request timeout, which is too short for Render's cold-start latency.
    try:
        httpx.get(
            f"http://127.0.0.1:{_BACKEND_PORT}/api/v1/reports/lot-summary",
            timeout=90.0,  # Allow up to 90 s for Render cold start
        )
    except Exception:
        pass  # Non-fatal — tests may still pass if the DB warms up in time

    yield  # E2E tests run here

    _kill(proc)  # Always stop the backend after all e2e tests complete


@pytest.fixture(scope="session")
def frontend_server(backend_server):
    """
    Build the React frontend and serve it via `vite preview` on port 5174.

    Using `vite preview` (pre-built static files) instead of `vite dev`
    avoids the multi-minute on-demand module compilation that occurs on the
    first browser request in dev mode, which caused Playwright tests to hang.

    Steps:
        1. `npm run build` — TypeScript compilation + Vite production bundle.
           This produces frontend/dist/ which vite preview serves.
        2. `npm run preview -- --port 5174 --strictPort` — Serves dist/ with
           the same /api → test-backend proxy as the dev server (configured
           via preview.proxy in frontend/vite.config.ts).

    Depends on backend_server to ensure the backend is ready before the
    frontend tries to proxy requests.

    The VITE_DEV_PROXY_TARGET env var is read by the preview.proxy section of
    frontend/vite.config.ts to direct /api calls to port 8001.

    Scope: "session" — one preview server shared across all e2e tests.

    Time complexity:  O(1) — single build + single server process.
    Space complexity: O(1) — constant number of subprocess handles.
    """
    env = {
        **os.environ,
        "VITE_DEV_PROXY_TARGET": f"http://127.0.0.1:{_BACKEND_PORT}",
    }
    # On Windows, npm is a .cmd script — it cannot be found by subprocess unless
    # we use shell=True or specify the .cmd suffix explicitly.
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    # Kill any zombie process holding the frontend port before rebuilding.
    _free_port(_FRONTEND_PORT)

    # ── Step 1: Build the frontend ─────────────────────────────────────────────
    # Use `build:e2e` (vite build only, no tsc) rather than `build` (tsc && vite
    # build) so TypeScript type errors in test files or missing @types/node don't
    # block the e2e run.  The production JS bundle does not require tsc to pass.
    build_result = subprocess.run(
        [npm_cmd, "run", "build:e2e"],
        cwd=str(_FRONTEND_DIR),
        env=env,
        capture_output=True,
    )
    if build_result.returncode != 0:
        pytest.fail(
            "Frontend build failed (npm run build:e2e).\n"
            f"Stdout: {build_result.stdout.decode()}\n"
            f"Stderr: {build_result.stderr.decode()}"
        )

    # ── Step 2: Serve the built files with vite preview ────────────────────────
    # --host 127.0.0.1 forces Vite to bind on IPv4 loopback.  Without this,
    # Vite binds to ::1 (IPv6 localhost) on Windows, but _wait_for polls
    # 127.0.0.1 (IPv4), causing a permanent connection-refused loop.
    proc = subprocess.Popen(
        [
            npm_cmd,
            "run",
            "preview",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            str(_FRONTEND_PORT),
            "--strictPort",  # Fail fast if port 5174 is already in use
        ],
        cwd=str(_FRONTEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        # Windows: CREATE_NEW_PROCESS_GROUP lets us send signals to the whole tree.
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0),
    )

    try:
        # vite preview starts much faster than vite dev (no compilation needed).
        _wait_for(f"http://127.0.0.1:{_FRONTEND_PORT}", timeout_s=30.0)
    except TimeoutError:
        # Kill the process BEFORE reading stderr.  proc.stderr.read() blocks
        # until EOF — which only arrives after the subprocess exits.  Calling
        # read() before kill() would deadlock forever.
        _kill(proc)
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        pytest.fail(
            f"Frontend preview server did not start on port {_FRONTEND_PORT}.\nStderr: {stderr}"
        )

    yield  # E2E tests run here

    _kill(proc)  # Always stop vite preview after all e2e tests complete


@pytest.fixture(scope="session")
def base_url(frontend_server) -> str:  # type: ignore[override]
    """
    Override pytest-playwright's base_url fixture.

    When pytest-playwright calls page.goto("/"), it prepends base_url.
    By returning our Vite preview server URL here, all playwright tests
    automatically target the correct server without writing the full URL.

    Returns:
        str: The base URL of the Vite preview server for e2e tests.
    """
    return f"http://127.0.0.1:{_FRONTEND_PORT}"
