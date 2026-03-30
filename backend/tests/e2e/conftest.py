# tests/e2e/conftest.py
#
# Pytest fixtures that start the backend and frontend dev servers for
# end-to-end (Playwright) tests.
#
# Server lifecycle (session-scoped):
#   1. backend_server  — starts uvicorn on port 8001 with TEST_DATABASE_URL so
#                        that e2e tests read real PostgreSQL data without touching
#                        the production database.
#   2. frontend_server — starts the Vite dev server on port 5174, proxying /api
#                        requests to the backend on port 8001 via the
#                        VITE_DEV_PROXY_TARGET env var (see frontend/vite.config.ts).
#   3. base_url        — overrides pytest-playwright's base_url fixture so that
#                        page.goto("/") resolves to http://localhost:5174.
#
# Skip behaviour:
#   If TEST_DATABASE_URL is not set in .env.test, all e2e tests are skipped
#   automatically (same as the integration tests).
#
# Prerequisites:
#   - TEST_DATABASE_URL in .env.test pointing at a real PostgreSQL database
#     (ops schema must exist with tables and triggers).
#   - Node.js installed (npm available on PATH).
#   - Playwright browser binaries installed:
#       poetry run playwright install
#   - All frontend npm deps installed:
#       cd frontend && npm install

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

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

# ── Port assignments ───────────────────────────────────────────────────────────
# Use non-standard ports so e2e tests don't collide with running dev servers.
_BACKEND_PORT = 8001
_FRONTEND_PORT = 5174


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


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def backend_server():
    """
    Start the FastAPI backend on port 8001 using the test PostgreSQL database.

    Environment:
        DATABASE_URL  — set to TEST_DATABASE_URL so the backend reads from the
                        test database, not the production one.
        TESTING       — set to "false" so _build_engine() uses PostgreSQL.
        ALLOWED_ORIGINS — includes the frontend test port (5174).

    The backend process is killed automatically when the test session ends.

    Scope: "session" — one backend instance shared across all e2e tests.
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
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        _kill(proc)
        pytest.fail(f"Backend server did not start on port {_BACKEND_PORT}.\nStderr: {stderr}")

    yield  # E2E tests run here

    _kill(proc)  # Always stop the backend after all e2e tests complete


@pytest.fixture(scope="session")
def frontend_server(backend_server):
    """
    Start the Vite dev server on port 5174, proxying /api to the test backend.

    Depends on backend_server to ensure the backend is ready before the
    frontend tries to proxy requests.

    The VITE_DEV_PROXY_TARGET env var is read by frontend/vite.config.ts to
    direct the /api proxy to port 8001 instead of the default 8000.

    Scope: "session" — one Vite instance shared across all e2e tests.
    """
    env = {
        **os.environ,
        "VITE_DEV_PROXY_TARGET": f"http://127.0.0.1:{_BACKEND_PORT}",
    }
    proc = subprocess.Popen(
        [
            "npm",
            "run",
            "dev",
            "--",
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
        _wait_for(f"http://127.0.0.1:{_FRONTEND_PORT}", timeout_s=60.0)
    except TimeoutError:
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        _kill(proc)
        pytest.fail(
            f"Frontend dev server did not start on port {_FRONTEND_PORT}.\nStderr: {stderr}"
        )

    yield  # E2E tests run here

    _kill(proc)  # Always stop Vite after all e2e tests complete


@pytest.fixture(scope="session")
def base_url(frontend_server) -> str:  # type: ignore[override]
    """
    Override pytest-playwright's base_url fixture.

    When pytest-playwright calls page.goto("/"), it prepends base_url.
    By returning our Vite dev server URL here, all playwright tests automatically
    target the correct server without needing to write the full URL.

    Returns:
        str: The base URL of the Vite dev server for e2e tests.
    """
    return f"http://127.0.0.1:{_FRONTEND_PORT}"
