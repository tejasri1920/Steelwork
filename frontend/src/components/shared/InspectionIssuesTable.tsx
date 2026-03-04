// src/components/shared/InspectionIssuesTable.tsx
//
// Table showing lots with flagged inspection records and their shipment status.
//
// Displayed on DashboardPage under the "Inspection Issues" tab.
// Supports AC5 (identify flagged lots) and AC6 (track shipment status).

import type { InspectionIssueRow } from '../../types';

/**
 * Props for the InspectionIssuesTable component.
 */
interface InspectionIssuesTableProps {
  /** Array of flagged inspection rows from GET /api/v1/reports/inspection-issues. */
  rows: InspectionIssueRow[];
}

/**
 * InspectionIssuesTable — table of lots with inspection issues.
 *
 * Columns (suggested):
 *   Lot ID | Inspection Result | Shipment Status | Ship Date | Destination
 *
 * Null shipment fields (lot not yet shipped) should display as "—".
 * A null shipment_status is particularly important to highlight — it means
 * a flagged lot has NO shipment record (gap in data, AC6).
 *
 * @param props - rows from the inspection-issues report endpoint
 *
 * AC5: Shows which lots have inspection problems.
 * AC6: Shows the shipment status of each flagged lot.
 */
export default function InspectionIssuesTable(_props: InspectionIssuesTableProps) {
  // TODO: Render a <table> with one <tr> per row.
  // Highlight rows where shipment_status is null (lot not shipped yet).
  // Handle empty rows with "No inspection issues found".
  throw new Error('TODO: Implement InspectionIssuesTable UI');
}
