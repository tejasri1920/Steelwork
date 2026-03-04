# app/database.py
#
# Database connection setup — creates the SQLAlchemy engine, session factory,
# and the Base class that all ORM models inherit from.
#
# Key concepts for someone new to SQLAlchemy:
#
#   Engine     : The low-level connection to the database. Think of it as the
#                "phone line" to PostgreSQL. Created once at startup.
#
#   Session    : A unit of work. You open a session, run queries, then close it.
#                Think of it as a "conversation" with the database.
#                Never share a session between requests — each HTTP request
#                gets its own session.
#
#   Base       : The parent class for all ORM models. When you write
#                `class Lot(Base)`, SQLAlchemy registers Lot as a table mapping.
#
#   get_db()   : A FastAPI "dependency" — a generator function that creates a
#                session for each HTTP request and closes it when the request ends.
#                FastAPI injects it into route handler parameters automatically.

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ── Declarative Base ──────────────────────────────────────────────────────────
# All ORM model classes inherit from Base.
# SQLAlchemy uses Base's metadata to know which tables exist and how they map
# to Python classes.
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Every model (Lot, ProductionRecord, etc.) inherits from this class.
    SQLAlchemy uses it to track all table definitions for schema creation
    and relationship resolution.
    """

    pass


# ── Engine factory ────────────────────────────────────────────────────────────


def _build_engine() -> Engine:
    """
    Creates and configures the SQLAlchemy database engine.

    The engine type depends on the TESTING environment variable:
      - TESTING=false (default): connects to PostgreSQL using DATABASE_URL.
        Sets search_path=ops so all queries target the `ops` schema by default.
      - TESTING=true: uses an in-memory SQLite database.
        SQLite is file-less and faster — ideal for unit tests that don't need
        a real PostgreSQL server.

    Why search_path=ops?
      The schema.sql creates tables inside the `ops` schema (not the default
      `public` schema). Setting search_path=ops at the connection level means
      all queries find tables like `lots` without needing to prefix them with
      `ops.lots` everywhere.

    Returns:
        A configured SQLAlchemy Engine instance.
    """
    if settings.is_testing:
        # SQLite in-memory: no file, no server, reset on every connection.
        # check_same_thread=False allows the same connection across threads (pytest may do this).
        return create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
    else:
        # PostgreSQL: connect_args passes "-c search_path=ops" so all unqualified table
        # names (e.g. "lots") resolve to the ops schema without needing "ops.lots" everywhere.
        pg_engine = create_engine(
            settings.database_url,
            connect_args={"options": "-c search_path=ops"},
        )
        return pg_engine


# Module-level engine: created once when this module is first imported.
engine = _build_engine()


# ── Session factory ────────────────────────────────────────────────────────────
# sessionmaker creates a factory that produces Session objects on demand.
# autocommit=False: you must call db.commit() explicitly (safer — no silent commits).
# autoflush=False:  don't automatically send pending changes to DB before queries.
# bind=engine:      all sessions use the engine created above.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── FastAPI dependency ─────────────────────────────────────────────────────────


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session to route handlers.

    Usage in a route:
        @router.get("/lots")
        def list_lots(db: Session = Depends(get_db)):
            ...

    How it works:
        1. FastAPI calls get_db() before your route function runs.
        2. get_db() creates a new Session and yields it to your route.
        3. Your route uses the session to run queries.
        4. After the route returns (or raises an exception), the `finally`
           block runs and closes the session — releasing the DB connection.

    Why use a generator (yield) instead of just returning?
        The `finally: db.close()` block runs even if an exception occurs.
        This guarantees the connection is always released, preventing leaks.
        A plain `return` would skip cleanup on errors.

    Yields:
        Session: An active database session for use in a single request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Always runs — releases the connection back to the pool
