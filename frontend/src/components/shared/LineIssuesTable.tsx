// src/components/shared/LineIssuesTable.tsx
//
// Table showing inspection issue counts and rates per production line.
//
// Displayed on DashboardPage under the "Line Issues" tab.
// Supports AC5 (which production lines have the most issues).

import type { LineIssueRow } from '../../types';

/**
 * Props for the LineIssuesTable component.
 */
interface LineIssuesTableProps {
  /** Array of per-line issue summaries from GET /api/v1/reports/line-issues. */
  rows: LineIssueRow[];
}

/**
 * LineIssuesTable — table of issue rates per production line.
 *
 * Columns (suggested):
 *   Production Line | Total Inspections | Total Issues | Issue Rate (%)
 *
 * Rows are already ordered by total_issues DESC (most problematic line first).
 *
 * @param props - rows from the line-issues report endpoint
 *
 * AC5: Identifies which production lines have the highest issue rates.
 */
export default function LineIssuesTable(_props: LineIssuesTableProps) {
  // TODO: Render a <table> with one <tr> per row.
  // Format issue_rate_pct as a percentage, e.g. "33.3%".
  // Handle empty rows with "No production or inspection data".
  throw new Error('TODO: Implement LineIssuesTable UI');
}
