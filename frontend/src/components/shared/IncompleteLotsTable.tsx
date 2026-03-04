// src/components/shared/IncompleteLotsTable.tsx
//
// Table showing lots that are missing production, inspection, or shipping data.
//
// Displayed on DashboardPage under the "Incomplete Lots" tab.
// Supports AC4 (surface missing data) and AC10 (completeness score).

import type { IncompleteLotRow } from '../../types';

/**
 * Props for the IncompleteLotsTable component.
 */
interface IncompleteLotsTableProps {
  /** Array of incomplete lot rows from GET /api/v1/reports/incomplete-lots. */
  rows: IncompleteLotRow[];
}

/**
 * IncompleteLotsTable — table of lots with missing data, most-incomplete first.
 *
 * Columns (suggested):
 *   Lot ID | Start Date | End Date | Production | Inspection | Shipping | Completeness
 *
 * For the Production/Inspection/Shipping columns, use MissingDataBadge to
 * visually highlight which domain is missing.
 *
 * @param props - rows from the incomplete-lots report endpoint
 *
 * AC4:  Analyst can identify which lots are missing data before a meeting.
 * AC10: Completeness score shown per row.
 */
export default function IncompleteLotsTable(_props: IncompleteLotsTableProps) {
  // TODO: Render a <table> with one <tr> per row.
  // Use MissingDataBadge for production/inspection/shipping columns.
  // Use CompletenessIndicator for the completeness column.
  // Handle empty rows with "All lots are complete".
  throw new Error('TODO: Implement IncompleteLotsTable UI');
}
