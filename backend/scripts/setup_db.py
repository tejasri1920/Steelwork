#!/usr/bin/env python
# backend/scripts/setup_db.py
#
# One-time database setup script.
#
# Creates the ops schema, all tables (derived from the ORM models so the column
# definitions match exactly what SQLAlchemy expects), and the PostgreSQL trigger
# functions that auto-maintain the data_completeness table.
#
# Why NOT apply db/schema.sql directly?
#   schema.sql was written with production-grade PostgreSQL enum types and some
#   column names that differ from the ORM.  The ORM uses VARCHAR / Integer for
#   all columns so it stays compatible with SQLite during unit tests.  Applying
#   schema.sql would create tables the ORM cannot INSERT into (wrong column
#   names, enum cast failures).  This script creates the simpler ORM-compatible
#   tables instead, then bolts on the trigger logic which is compatible with
#   both column sets.
#
# Usage (from the project root):
#   python backend/scripts/setup_db.py
#
# The DATABASE_URL is read from .env in the project root.
# Idempotent: safe to run more than once — CREATE IF NOT EXISTS everywhere.

import os
import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────
# Add backend/ to sys.path so `from app.database import Base` works.
_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

# ── Load .env ──────────────────────────────────────────────────────────────────
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=False)

DB_URL: str = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL is not set in .env", file=sys.stderr)
    sys.exit(1)

# SQLAlchemy 2.x requires the postgresql:// scheme; Render sometimes gives postgres://
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

# ── Imports ────────────────────────────────────────────────────────────────────
from sqlalchemy import create_engine, text  # noqa: E402

import app.models.data_completeness  # noqa: E402, F401
import app.models.inspection  # noqa: E402, F401
import app.models.lot  # noqa: E402, F401
import app.models.production  # noqa: E402, F401
import app.models.shipping  # noqa: E402, F401

# Import ALL models so Base.metadata knows about every table before create_all().
from app.database import Base  # noqa: E402

# ── Engine ─────────────────────────────────────────────────────────────────────
# search_path=ops means unqualified table names (e.g. "lots") resolve to ops.lots.
engine = create_engine(
    DB_URL,
    connect_args={"options": "-c search_path=ops"},
)

# ── Step 1: Create the ops schema ──────────────────────────────────────────────
print("Creating ops schema (if not exists)…")
with engine.connect() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS ops"))
    conn.commit()

# ── Step 2: Create tables from ORM definitions ────────────────────────────────
# Base.metadata.create_all emits CREATE TABLE IF NOT EXISTS for every model.
# With search_path=ops the tables land in the ops schema.
print("Creating tables from ORM models (if not exist)…")
Base.metadata.create_all(engine)

# ── Step 3: Install PostgreSQL trigger functions ───────────────────────────────
# These functions are pure SQL and compatible with the ORM column names.
# CREATE OR REPLACE means they are safe to re-run.
print("Installing trigger functions and triggers…")

_TRIGGER_SQL = """
-- ─────────────────────────────────────────────────────────────────────────────
-- Trigger 1: auto-set updated_at on every UPDATE
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION ops.fn_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_lots_updated_at'
    ) THEN
        CREATE TRIGGER trg_lots_updated_at
            BEFORE UPDATE ON ops.lots
            FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_production_updated_at'
    ) THEN
        CREATE TRIGGER trg_production_updated_at
            BEFORE UPDATE ON ops.production_records
            FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_inspection_updated_at'
    ) THEN
        CREATE TRIGGER trg_inspection_updated_at
            BEFORE UPDATE ON ops.inspection_records
            FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_shipping_updated_at'
    ) THEN
        CREATE TRIGGER trg_shipping_updated_at
            BEFORE UPDATE ON ops.shipping_records
            FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();
    END IF;
END $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- Trigger 2: initialise data_completeness row when a new lot is created
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION ops.fn_init_data_completeness()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO ops.data_completeness (lot_id)
    VALUES (NEW.lot_id)
    ON CONFLICT (lot_id) DO NOTHING;
    RETURN NEW;
END;
$$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_lots_init_completeness'
    ) THEN
        CREATE TRIGGER trg_lots_init_completeness
            AFTER INSERT ON ops.lots
            FOR EACH ROW EXECUTE FUNCTION ops.fn_init_data_completeness();
    END IF;
END $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- Trigger 3: recalculate data_completeness on any child-record change
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION ops.fn_refresh_data_completeness()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_lot_id   INTEGER;
    v_has_prod BOOLEAN;
    v_has_insp BOOLEAN;
    v_has_ship BOOLEAN;
    v_score    SMALLINT;
BEGIN
    v_lot_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.lot_id ELSE NEW.lot_id END;
    IF v_lot_id IS NULL THEN
        RETURN NULL;
    END IF;

    v_has_prod := EXISTS (SELECT 1 FROM ops.production_records WHERE lot_id = v_lot_id);
    v_has_insp := EXISTS (SELECT 1 FROM ops.inspection_records  WHERE lot_id = v_lot_id);
    v_has_ship := EXISTS (SELECT 1 FROM ops.shipping_records    WHERE lot_id = v_lot_id);

    v_score := ROUND(
        (v_has_prod::INT + v_has_insp::INT + v_has_ship::INT) * 100.0 / 3
    )::SMALLINT;

    INSERT INTO ops.data_completeness
        (lot_id, has_production_data, has_inspection_data, has_shipping_data,
         overall_completeness, updated_at)
    VALUES
        (v_lot_id, v_has_prod, v_has_insp, v_has_ship, v_score, now())
    ON CONFLICT (lot_id) DO UPDATE SET
        has_production_data  = EXCLUDED.has_production_data,
        has_inspection_data  = EXCLUDED.has_inspection_data,
        has_shipping_data    = EXCLUDED.has_shipping_data,
        overall_completeness = EXCLUDED.overall_completeness,
        updated_at           = EXCLUDED.updated_at;

    RETURN NULL;
END;
$$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_production_completeness'
    ) THEN
        CREATE TRIGGER trg_production_completeness
            AFTER INSERT OR UPDATE OR DELETE ON ops.production_records
            FOR EACH ROW EXECUTE FUNCTION ops.fn_refresh_data_completeness();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_inspection_completeness'
    ) THEN
        CREATE TRIGGER trg_inspection_completeness
            AFTER INSERT OR UPDATE OR DELETE ON ops.inspection_records
            FOR EACH ROW EXECUTE FUNCTION ops.fn_refresh_data_completeness();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_shipping_completeness'
    ) THEN
        CREATE TRIGGER trg_shipping_completeness
            AFTER INSERT OR UPDATE OR DELETE ON ops.shipping_records
            FOR EACH ROW EXECUTE FUNCTION ops.fn_refresh_data_completeness();
    END IF;
END $$;
"""

# Execute the trigger SQL in a single transaction.
# Each statement is separated by a semicolon; we split on double-newlines
# between DO blocks and CREATE statements to handle multi-line function bodies.
with engine.connect() as conn:
    conn.execute(text(_TRIGGER_SQL))
    conn.commit()

print()
print("Done! Database is ready.")
print("  Schema:  ops")
print("  Tables:  lots, production_records, inspection_records,")
print("           shipping_records, data_completeness")
print("  Triggers: updated_at, init_completeness, refresh_completeness")
