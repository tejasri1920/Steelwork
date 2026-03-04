// src/components/shared/LotSummaryTable.tsx
//
// Table showing the aggregated lot summary (one row per lot).
//
// Displayed on DashboardPage under the "Summary" tab.
// Each row links to the lot's detail page (/lots/{lot_code}).
//
// Supports AC1 (cross-function view), AC7 (meeting summary), AC8 (shipment status),
// AC10 (completeness score per row).

import type { LotSummaryRow } from '../../types';

/**
 * Props for the LotSummaryTable component.
 */
interface LotSummaryTableProps {
  /** Array of aggregated lot rows from GET /api/v1/reports/lot-summary. */
  rows: LotSummaryRow[];
}

/**
 * LotSummaryTable — data table rendering one aggregated row per lot.
 *
 * Columns (suggested):
 *   Lot ID | Start Date | End Date | Total Produced | Lines Used |
 *   Any Issues | Issue Count | Latest Status | Completeness
 *
 * Each row in the "Lot ID" column should be a <Link> to /lots/{lot_id}.
 * Note: The lot_id is an integer in this report. Use lot_id for the link
 * OR cross-reference with the lots list if lot_code is needed.
 *
 * Null values (e.g. total_produced for a lot with no production) should
 * display as "—" (em dash) rather than "null".
 *
 * @param props - rows array from the lot-summary report endpoint
 *
 * AC1:  Shows production, inspection, and shipping data in one place.
 * AC7:  One row per lot — clean format for meetings.
 * AC8:  latest_status column.
 * AC10: overall_completeness column.
 */
export default function LotSummaryTable(_props: LotSummaryTableProps) {
  // TODO: Render a <table> with one <tr> per row.
  // Handle empty rows with an appropriate "No data" message.
  // Use CompletenessIndicator for the completeness column.
  throw new Error('TODO: Implement LotSummaryTable UI');
}
