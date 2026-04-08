// src/types/index.ts
//
// TypeScript interfaces that mirror the Pydantic response schemas from the backend.
//
// These types are used throughout the frontend for:
//   - API function return types (src/api/client.ts)
//   - Component props
//   - React Query data types
//
// Naming: interfaces match the Pydantic schema names from backend/app/schemas/.
// Optional fields (?) correspond to `Optional[...]` in Python (can be null in JSON).
//
// AC coverage in this file:
//   AC2  — LotSummary (lot_code, dates)
//   AC3  — LotSummary (start_date, end_date for filtering)
//   AC4  — LotSummary + IncompleteLotRow (has_*_data, overall_completeness)
//   AC5  — LineIssueRow (issue_rate_pct per line)
//   AC6  — InspectionIssueRow (issue_flag + shipment_status)
//   AC7  — LotSummaryRow (aggregated meeting view)
//   AC8  — LotSummaryRow.latest_status (shipment state)
//   AC9  — LotDetail (all child records)
//   AC10 — overall_completeness field on multiple types


// ── Child record types ────────────────────────────────────────────────────────
// Nested inside LotDetail — mirror ProductionRecordOut, InspectionRecordOut,
// ShippingRecordOut Pydantic schemas.

/** One production run record (mirrors ProductionRecordOut). */
export interface ProductionRecord {
  production_id: number;
  production_date: string;       // ISO-8601 date string, e.g. "2026-01-12"
  production_line: string;       // 'Line 1' | 'Line 2' | 'Line 3' | 'Line 4'
  quantity_produced: number;
  shift: string;                 // 'Day' | 'Swing' | 'Night'
  part_number: string;
  units_planned: number;
  downtime_min: number;
  line_issue: boolean;
  primary_issue: string | null;  // null when line_issue = false
  supervisor_notes: string | null;
}

/** One quality inspection record (mirrors InspectionRecordOut). */
export interface InspectionRecord {
  inspection_id: number;
  inspection_date: string;       // ISO-8601 date string
  inspector_id: string;
  inspection_result: string;     // 'Pass' | 'Fail' | 'Conditional'
  issue_flag: boolean;
  issue_category: string | null; // null when issue_flag = false
  defect_count: number;
  sample_size: number;
  notes: string | null;
}

/** One shipment record (mirrors ShippingRecordOut). */
export interface ShippingRecord {
  shipping_id: number;
  ship_date: string;             // ISO-8601 date string
  carrier: string;
  tracking_number: string | null; // null until carrier provides it
  destination: string;
  quantity_shipped: number;
  shipment_status: string;       // 'Pending' | 'In Transit' | 'Delivered' | 'On Hold'
  notes: string | null;
}


// ── Lot types ─────────────────────────────────────────────────────────────────

/**
 * Lightweight lot row returned by GET /api/v1/lots (mirrors LotSummary).
 * AC2, AC3, AC4, AC10.
 */
export interface LotSummary {
  lot_id: number;
  lot_code: string;
  start_date: string;             // ISO-8601 date string
  end_date: string | null;        // null for lots still in progress
  has_production_data: boolean;
  has_inspection_data: boolean;
  has_shipping_data: boolean;
  overall_completeness: number;   // 0 | 33 | 67 | 100
}

/**
 * Full lot detail returned by GET /api/v1/lots/{lot_code} (mirrors LotDetail).
 * AC9.
 */
export interface LotDetail {
  lot_id: number;
  lot_code: string;
  start_date: string;
  end_date: string | null;
  production_records: ProductionRecord[];
  inspection_records: InspectionRecord[];
  shipping_records: ShippingRecord[];
  has_production_data: boolean;
  has_inspection_data: boolean;
  has_shipping_data: boolean;
  overall_completeness: number;
  created_at: string;             // ISO-8601 datetime string
  updated_at: string;
}


// ── Report types ──────────────────────────────────────────────────────────────

/**
 * One row of the aggregated lot summary report (mirrors LotSummaryRow).
 * GET /api/v1/reports/lot-summary — AC1, AC7, AC8, AC10.
 */
export interface LotSummaryRow {
  lot_id: number;
  lot_code: string;                // Human-readable identifier, e.g. "LOT-001"
  start_date: string;
  end_date: string | null;
  total_produced: number | null;   // null if no production records
  lines_used: string | null;       // null if no production records
  any_issues: boolean | null;      // null if no inspection records
  issue_count: number | null;      // null if no inspection records
  latest_status: string | null;    // null if no shipping records
  overall_completeness: number;
}

/**
 * One row of the inspection issues report (mirrors InspectionIssueRow).
 * GET /api/v1/reports/inspection-issues — AC5, AC6.
 */
export interface InspectionIssueRow {
  lot_id: number;
  lot_code: string;                // Human-readable identifier for display
  inspection_result: string;
  issue_flag: boolean;             // Always true in this report
  shipment_status: string | null;  // null if no shipping record yet
  ship_date: string | null;
  destination: string | null;
}

/**
 * One row of the incomplete lots report (mirrors IncompleteLotRow).
 * GET /api/v1/reports/incomplete-lots — AC4, AC10.
 */
export interface IncompleteLotRow {
  lot_id: number;
  lot_code: string;                // Human-readable identifier for display
  start_date: string;
  end_date: string | null;
  has_production_data: boolean;
  has_inspection_data: boolean;
  has_shipping_data: boolean;
  overall_completeness: number;    // 0 | 33 | 67 (never 100 in this report)
}

/**
 * One row of the line issues report (mirrors LineIssueRow).
 * GET /api/v1/reports/line-issues — AC5.
 */
export interface LineIssueRow {
  production_line: string;
  total_inspections: number;
  total_issues: number;
  issue_rate_pct: number;          // Percentage, e.g. 33.3
}


// ── API helper types ──────────────────────────────────────────────────────────

/** Query parameters for GET /api/v1/lots */
export interface LotListParams {
  start_date?: string;   // ISO-8601 date, e.g. "2026-01-01"
  end_date?: string;     // ISO-8601 date, e.g. "2026-01-31"
}
