# app/config.py
#
# Application settings — reads environment variables into a typed Python class.
#
# How it works:
#   pydantic-settings reads values from (in priority order):
#     1. Real environment variables (e.g., set in Docker Compose or your shell)
#     2. A .env file in the project root (for local development)
#     3. Default values defined here (fallback)
#
# Why use this instead of os.environ.get()?
#   - Type safety: DATABASE_URL is always a string; BACKEND_PORT is always an int.
#   - Single source of truth: all env vars are declared in one place.
#   - Validation: pydantic raises a clear error at startup if a required var is missing.
#
# Usage:
#   from app.config import settings
#   print(settings.database_url)

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All environment variables the application needs, declared as typed fields.

    pydantic-settings automatically maps environment variable names to field
    names (case-insensitive). For example, DATABASE_URL env var → database_url field.
    """

    # ── Database ───────────────────────────────────────────────────────────────
    # Full PostgreSQL connection string.
    # Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE
    # In Docker, HOST is "db" (the Docker Compose service name).
    # In tests, this is overridden by the TESTING flag (see database.py).
    database_url: str

    # ── API ────────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed browser origins for CORS.
    # Example: "http://localhost:5173,http://localhost:3000"
    # CORS (Cross-Origin Resource Sharing) controls which websites can call this API.
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Log level passed to uvicorn/Python logging.
    # Valid values: "debug", "info", "warning", "error", "critical"
    log_level: str = "info"

    # ── Test mode ─────────────────────────────────────────────────────────────
    # Set TESTING=true in your shell to switch the database engine to SQLite.
    # SQLite is a lightweight file-based database that runs in memory during tests.
    # This means tests never need a running PostgreSQL server.
    testing: bool = False

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def allowed_origins_list(self) -> list[str]:
        """
        Splits the comma-separated ALLOWED_ORIGINS string into a Python list.

        FastAPI's CORSMiddleware expects a list, not a single string.
        Example: "http://a.com,http://b.com" → ["http://a.com", "http://b.com"]
        """
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_testing(self) -> bool:
        """
        Returns True when the app is running in test mode.

        Used by database.py to choose between SQLite (tests) and PostgreSQL (production).
        """
        return self.testing

    # Tells pydantic-settings to also read from a .env file.
    # env_file = ".env" looks for the file relative to the working directory.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Module-level singleton: import this everywhere instead of instantiating Settings().
# Singleton means it is created once and reused — avoids re-reading the .env file
# on every import.
settings = Settings()
