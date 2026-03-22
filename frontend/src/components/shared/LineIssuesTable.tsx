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
 * Columns:
 *   Production Line | Total Inspections | Total Issues | Issue Rate (%)
 *
 * Rows are already ordered by total_issues DESC (most problematic line first).
 * issue_rate_pct is formatted as a percentage, e.g. "33.3%".
 *
 * @param props - rows from the line-issues report endpoint
 *
 * AC5: Identifies which production lines have the highest issue rates.
 */
export default function LineIssuesTable({ rows }: LineIssuesTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-gray-500 text-sm py-4">No production or inspection data.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border border-gray-200 rounded">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-2 text-left">Production Line</th>
            <th className="px-4 py-2 text-right">Total Inspections</th>
            <th className="px-4 py-2 text-right">Total Issues</th>
            <th className="px-4 py-2 text-right">Issue Rate</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row) => {
            const rate = Number(row.issue_rate_pct);
            // Colour-code the rate: red ≥50%, amber <50% and >0%, green = 0%.
            const rateClass =
              rate >= 50
                ? 'text-red-600 font-semibold'
                : rate > 0
                  ? 'text-amber-600'
                  : 'text-green-600';

            return (
              <tr key={row.production_line} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{row.production_line}</td>
                <td className="px-4 py-2 text-right">{row.total_inspections}</td>
                <td className="px-4 py-2 text-right">{row.total_issues}</td>
                <td className={`px-4 py-2 text-right ${rateClass}`}>
                  {rate.toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
