// src/components/shared/InspectionIssuesTable.tsx
//
// Table showing lots with flagged inspection records and their shipment status.
//
// Displayed on DashboardPage under the "Inspection Issues" tab.
// Supports AC5 (identify flagged lots) and AC6 (track shipment status).

import type { InspectionIssueRow } from '../../types';

/** Helper: render "—" for null/undefined values. */
const dash = (value: unknown) => (value === null || value === undefined ? '—' : String(value));

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
 * Columns:
 *   Lot ID | Inspection Result | Shipment Status | Ship Date | Destination
 *
 * Rows where shipment_status is null are highlighted in amber — they represent
 * flagged lots that have no shipment record at all (AC6: gap in data).
 *
 * @param props - rows from the inspection-issues report endpoint
 *
 * AC5: Shows which lots have inspection problems.
 * AC6: Shows the shipment status of each flagged lot.
 */
export default function InspectionIssuesTable({ rows }: InspectionIssuesTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-gray-500 text-sm py-4">No inspection issues found.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border border-gray-200 rounded">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-2 text-left">Lot ID</th>
            <th className="px-4 py-2 text-left">Inspection Result</th>
            <th className="px-4 py-2 text-left">Shipment Status</th>
            <th className="px-4 py-2 text-left">Ship Date</th>
            <th className="px-4 py-2 text-left">Destination</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, idx) => {
            // Highlight rows with no shipment record — flagged but not yet actioned (AC6).
            const rowClass = row.shipment_status === null
              ? 'bg-amber-50 hover:bg-amber-100'
              : 'hover:bg-gray-50';

            return (
              <tr key={idx} className={rowClass}>
                <td className="px-4 py-2 font-medium">{row.lot_code}</td>
                <td className="px-4 py-2">
                  <span className={row.inspection_result === 'Fail' ? 'text-red-600 font-semibold' : ''}>
                    {row.inspection_result}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {row.shipment_status === 'On Hold'
                    ? <span className="text-red-600 font-semibold">On Hold</span>
                    : dash(row.shipment_status)}
                </td>
                <td className="px-4 py-2">{dash(row.ship_date)}</td>
                <td className="px-4 py-2">{dash(row.destination)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
