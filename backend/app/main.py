# app/main.py
#
# FastAPI application factory.
#
# This is the entry point for the backend server. It:
#   1. Creates the FastAPI app instance with metadata
#   2. Configures CORS (Cross-Origin Resource Sharing) so the React frontend can call the API
#   3. Registers all APIRouters under the /api/v1 prefix
#   4. Provides a health-check endpoint at GET /health
#   5. Initialises application logging on startup via setup_logging()
#
# The app object is what uvicorn serves:
#   uvicorn app.main:app --host 0.0.0.0 --port 8000
#
# In Docker, the CMD in backend/Dockerfile runs:
#   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Using `python -m uvicorn` (module mode) avoids shebang path issues in containers.

import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging
from app.routers import lots, reports

# Module-level logger — records startup / shutdown milestones.
# Name follows __name__ convention: "app.main" in the log output.
logger = logging.getLogger(__name__)

# ── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Steelworks Ops Analytics API",
    description=(
        "Operations Analytics API — unifies Production, Inspection, and Shipping data "
        "by Lot ID for operations analysts. Supports 10 acceptance criteria (AC1–AC10)."
    ),
    version="0.1.0",
    # /docs → Swagger UI (interactive API explorer)
    # /redoc → ReDoc (read-only API documentation)
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS middleware ───────────────────────────────────────────────────────────
# CORS must be added BEFORE registering routers so it applies to all routes.
#
# allowed_origins_list is a property on Settings that splits the
# comma-separated ALLOWED_ORIGINS env var into a Python list.
# Example: "http://localhost:5173,http://localhost:3000" →
#          ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,  # Only listed origins can call the API
    allow_credentials=True,  # Allow cookies / Authorization headers
    allow_methods=["*"],  # Allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Allow Content-Type, Authorization, etc.
)

# ── Router registration ───────────────────────────────────────────────────────
# Each include_router call adds all the router's endpoints to the app.
# prefix="/api/v1" is prepended to all route paths:
#   lots.router has prefix="/lots"    → full path: /api/v1/lots
#   reports.router has prefix="/reports" → full path: /api/v1/reports

app.include_router(lots.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


# ── Startup / Shutdown events ─────────────────────────────────────────────────


@app.on_event("startup")  # type: ignore[attr-defined]
async def startup_event() -> None:
    """
    Initialise logging and record the application startup milestone.

    Logging setup is skipped when settings.testing is True so that
    pytest's own log-capture machinery (caplog) is not overridden and no
    app.log file is created in the test working directory.

    Time complexity:  O(1)
    Space complexity: O(1)
    """
    if not settings.testing:
        # Set up console + rotating-file handlers (see logging_config.py).
        # In tests TESTING=true so this branch is skipped; caplog captures logs
        # directly from the loggers without needing file or stream handlers.
        setup_logging()

        # Initialise Sentry error monitoring when a DSN is configured.
        # Sentry captures unhandled exceptions and sends them to sentry.io,
        # giving us real-time alerts for production errors.
        #
        # Options:
        #   send_default_pii=False  — never attach user IP / cookies to events (GDPR safe)
        #   traces_sample_rate=0.0  — disable performance tracing (we only want error alerts)
        #   enable_logs=False       — don't forward Python log records to Sentry
        #
        # When sentry_dsn is None (local dev), this is a no-op.
        if settings.sentry_dsn:
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                send_default_pii=False,
                traces_sample_rate=0.0,
                enable_logs=False,
            )
            logger.info("Sentry initialised")

    logger.info(
        "Application startup complete | version=%s | testing=%s",
        app.version,
        settings.testing,
    )


@app.on_event("shutdown")  # type: ignore[attr-defined]
async def shutdown_event() -> None:
    """
    Record the application shutdown milestone.

    Time complexity:  O(1)
    Space complexity: O(1)
    """
    logger.info("Application shutdown")


# ── Health check ──────────────────────────────────────────────────────────────


@app.api_route(
    "/health",
    methods=["GET", "HEAD"],
    tags=["health"],
    summary="Health check — returns 200 OK if the server is up",
    description="Used by UptimeRobot (HEAD), Docker Compose, and load balancers to verify the backend is running.",
)
def health_check() -> dict[str, str]:
    """
    Return a simple JSON status message.

    Returns:
        HTTP 200 {"status": "ok"}

    This does NOT check the database connection — it only verifies the server is up.
    A separate /health/db endpoint could be added later for DB liveness checks.
    """
    logger.debug("Health check requested")
    return {"status": "ok"}
