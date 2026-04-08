#!/usr/bin/env python3
"""
backend/scripts/seed_dev_db.py

Seeds the development/production database with sample lot data.
Uses only columns defined in the ORM models (compatible with setup_db.py tables).

Usage (from backend/ directory):
    poetry run python scripts/seed_dev_db.py

Safe to re-run: clears existing rows before inserting.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(1)
db_url = db_url.replace("postgres://", "postgresql://")

from sqlalchemy import create_engine, text  # noqa: E402

engine = create_engine(db_url, connect_args={"options": "-c search_path=ops"})

SEED = """
DELETE FROM ops.shipping_records;
DELETE FROM ops.inspection_records;
DELETE FROM ops.production_records;
DELETE FROM ops.data_completeness;
DELETE FROM ops.lots;

INSERT INTO ops.lots (lot_code, start_date, end_date) VALUES
  ('LOT-20251215-001', '2025-12-15', '2025-12-20'),
  ('LOT-20251216-001', '2025-12-16', '2025-12-21'),
  ('LOT-20251217-001', '2025-12-17', '2025-12-22'),
  ('LOT-20251220-001', '2025-12-20', '2025-12-24'),
  ('LOT-20251222-001', '2025-12-22', '2025-12-27'),
  ('LOT-20251224-001', '2025-12-24', '2025-12-29'),
  ('LOT-20260103-001', '2026-01-03', '2026-01-08'),
  ('LOT-20260105-001', '2026-01-05', '2026-01-10'),
  ('LOT-20260108-001', '2026-01-08', '2026-01-13'),
  ('LOT-20260110-001', '2026-01-10', '2026-01-15'),
  ('LOT-20260115-001', '2026-01-15', '2026-01-20'),
  ('LOT-20260120-001', '2026-01-20', NULL);

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2025-12-15', 'Line 1', 480, 'Day', 'SW-8091-A', 500, 0, false
  FROM ops.lots WHERE lot_code='LOT-20251215-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2025-12-16', 'Line 2', 500, 'Day', 'SW-8091-B', 500, 0, false
  FROM ops.lots WHERE lot_code='LOT-20251216-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue, primary_issue)
  SELECT lot_id, '2025-12-17', 'Line 3', 390, 'Night', 'SW-9100-C', 400, 45, true, 'Tool wear'
  FROM ops.lots WHERE lot_code='LOT-20251217-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2025-12-20', 'Line 1', 500, 'Day', 'SW-7020-D', 500, 10, false
  FROM ops.lots WHERE lot_code='LOT-20251220-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2025-12-22', 'Line 4', 300, 'Swing', 'SW-4451-E', 320, 20, false
  FROM ops.lots WHERE lot_code='LOT-20251222-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2025-12-24', 'Line 2', 450, 'Day', 'SW-8091-A', 450, 0, false
  FROM ops.lots WHERE lot_code='LOT-20251224-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2026-01-03', 'Line 1', 500, 'Day', 'SW-8091-A', 500, 5, false
  FROM ops.lots WHERE lot_code='LOT-20260103-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue, primary_issue)
  SELECT lot_id, '2026-01-05', 'Line 3', 350, 'Night', 'SW-9100-C', 400, 60, true, 'Machine fault'
  FROM ops.lots WHERE lot_code='LOT-20260105-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2026-01-08', 'Line 2', 480, 'Day', 'SW-7020-D', 480, 0, false
  FROM ops.lots WHERE lot_code='LOT-20260108-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2026-01-10', 'Line 4', 200, 'Day', 'SW-4451-E', 200, 0, false
  FROM ops.lots WHERE lot_code='LOT-20260110-001';

INSERT INTO ops.production_records
  (lot_id, production_date, production_line, quantity_produced, shift, part_number, units_planned, downtime_min, line_issue)
  SELECT lot_id, '2026-01-15', 'Line 1', 500, 'Day', 'SW-8091-A', 500, 0, false
  FROM ops.lots WHERE lot_code='LOT-20260115-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, defect_count, sample_size)
  SELECT lot_id, '2025-12-16', 'EMP-001', 'Pass', false, 0, 50
  FROM ops.lots WHERE lot_code='LOT-20251215-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, defect_count, sample_size)
  SELECT lot_id, '2025-12-17', 'EMP-002', 'Pass', false, 1, 50
  FROM ops.lots WHERE lot_code='LOT-20251216-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, issue_category, defect_count, sample_size)
  SELECT lot_id, '2025-12-18', 'EMP-042', 'Fail', true, 'Dimensional', 14, 50
  FROM ops.lots WHERE lot_code='LOT-20251217-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, defect_count, sample_size)
  SELECT lot_id, '2025-12-21', 'EMP-001', 'Pass', false, 0, 50
  FROM ops.lots WHERE lot_code='LOT-20251220-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, issue_category, defect_count, sample_size)
  SELECT lot_id, '2025-12-23', 'EMP-007', 'Conditional', true, 'Surface finish', 3, 50
  FROM ops.lots WHERE lot_code='LOT-20251222-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, defect_count, sample_size)
  SELECT lot_id, '2025-12-25', 'EMP-002', 'Pass', false, 0, 50
  FROM ops.lots WHERE lot_code='LOT-20251224-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, defect_count, sample_size)
  SELECT lot_id, '2026-01-04', 'EMP-001', 'Pass', false, 0, 50
  FROM ops.lots WHERE lot_code='LOT-20260103-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, issue_category, defect_count, sample_size)
  SELECT lot_id, '2026-01-06', 'EMP-042', 'Fail', true, 'Hardness', 9, 50
  FROM ops.lots WHERE lot_code='LOT-20260105-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, defect_count, sample_size)
  SELECT lot_id, '2026-01-09', 'EMP-007', 'Pass', false, 0, 50
  FROM ops.lots WHERE lot_code='LOT-20260108-001';

INSERT INTO ops.inspection_records
  (lot_id, inspection_date, inspector_id, inspection_result, issue_flag, defect_count, sample_size)
  SELECT lot_id, '2026-01-11', 'EMP-001', 'Pass', false, 2, 50
  FROM ops.lots WHERE lot_code='LOT-20260110-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2025-12-22', 'FedEx Freight', 'Detroit Assembly Plant', 480, 'Delivered'
  FROM ops.lots WHERE lot_code='LOT-20251215-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2025-12-23', 'UPS LTL', 'Chicago Distribution Center', 500, 'Delivered'
  FROM ops.lots WHERE lot_code='LOT-20251216-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2025-12-20', 'FedEx Freight', 'Cleveland Warehouse', 390, 'On Hold'
  FROM ops.lots WHERE lot_code='LOT-20251217-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2025-12-26', 'Old Dominion', 'Minneapolis Plant', 500, 'Delivered'
  FROM ops.lots WHERE lot_code='LOT-20251220-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2025-12-28', 'XPO Logistics', 'Columbus Hub', 300, 'In Transit'
  FROM ops.lots WHERE lot_code='LOT-20251222-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2025-12-30', 'FedEx Freight', 'Detroit Assembly Plant', 450, 'Delivered'
  FROM ops.lots WHERE lot_code='LOT-20251224-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2026-01-10', 'UPS LTL', 'Chicago Distribution Center', 500, 'In Transit'
  FROM ops.lots WHERE lot_code='LOT-20260103-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2026-01-08', 'Old Dominion', 'Cleveland Warehouse', 350, 'On Hold'
  FROM ops.lots WHERE lot_code='LOT-20260105-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2026-01-15', 'FedEx Freight', 'Minneapolis Plant', 480, 'Shipped'
  FROM ops.lots WHERE lot_code='LOT-20260108-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2026-01-18', 'XPO Logistics', 'Detroit Assembly Plant', 200, 'Shipped'
  FROM ops.lots WHERE lot_code='LOT-20260110-001';

INSERT INTO ops.shipping_records
  (lot_id, ship_date, carrier, destination, quantity_shipped, shipment_status)
  SELECT lot_id, '2026-01-22', 'UPS LTL', 'Columbus Hub', 500, 'Shipped'
  FROM ops.lots WHERE lot_code='LOT-20260115-001';
"""

with engine.connect() as conn:
    for stmt in SEED.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(text(stmt))
    conn.commit()

print("Done! 12 lots seeded with production, inspection, and shipping records.")
