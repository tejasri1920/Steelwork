# app/main.py
#
# FastAPI application factory.
#
# This is the entry point for the backend server. It:
#   1. Creates the FastAPI app instance with metadata
#   2. Configures CORS (Cross-Origin Resource Sharing) so the React frontend can call the API
#   3. Registers all APIRouters under the /api/v1 prefix
#   4. Provides a health-check endpoint at GET /health
#
# The app object is what uvicorn serves:
#   uvicorn app.main:app --host 0.0.0.0 --port 8000
#
# In Docker, the CMD in backend/Dockerfile runs:
#   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Using `python -m uvicorn` (module mode) avoids shebang path issues in containers.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import lots, reports

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


# ── Health check ──────────────────────────────────────────────────────────────


@app.get(
    "/health",
    tags=["health"],
    summary="Health check — returns 200 OK if the server is up",
    description="Used by Docker Compose and load balancers to verify the backend is running.",
)
def health_check() -> dict[str, str]:
    """
    Return a simple JSON status message.

    Returns:
        HTTP 200 {"status": "ok"}

    This does NOT check the database connection — it only verifies the server is up.
    A separate /health/db endpoint could be added later for DB liveness checks.
    """
    return {"status": "ok"}
