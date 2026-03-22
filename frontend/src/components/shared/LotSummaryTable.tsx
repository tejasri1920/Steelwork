// src/components/shared/LotSummaryTable.tsx
//
// Table showing the aggregated lot summary (one row per lot).
//
// Displayed on DashboardPage under the "Summary" tab.
// Each Lot ID links to the lot's detail page (/lots/{lot_id}).
//
// Supports AC1 (cross-function view), AC7 (meeting summary), AC8 (shipment status),
// AC10 (completeness score per row).

import { Link } from 'react-router-dom';

import CompletenessIndicator from './CompletenessIndicator';
import type { LotSummaryRow } from '../../types';

/** Helper: render "—" for null/undefined values. */
const dash = (value: unknown) => (value === null || value === undefined ? '—' : String(value));

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
 * Columns:
 *   Lot ID | Start Date | End Date | Total Produced | Lines Used |
 *   Any Issues | Issue Count | Latest Status | Completeness
 *
 * Null values display as "—" (em dash).
 * The Lot ID cell links to /lots/{lot_id} for the full detail view (AC9).
 *
 * @param props - rows array from the lot-summary report endpoint
 *
 * AC1:  Shows production, inspection, and shipping data in one place.
 * AC7:  One row per lot — clean format for meetings.
 * AC8:  latest_status column.
 * AC10: overall_completeness column.
 */
export default function LotSummaryTable({ rows }: LotSummaryTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-gray-500 text-sm py-4">No lots found.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border border-gray-200 rounded">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-2 text-left">Lot ID</th>
            <th className="px-4 py-2 text-left">Start Date</th>
            <th className="px-4 py-2 text-left">End Date</th>
            <th className="px-4 py-2 text-right">Total Produced</th>
            <th className="px-4 py-2 text-left">Lines Used</th>
            <th className="px-4 py-2 text-center">Any Issues</th>
            <th className="px-4 py-2 text-right">Issue Count</th>
            <th className="px-4 py-2 text-left">Latest Status</th>
            <th className="px-4 py-2 text-center">Completeness</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row) => (
            <tr key={row.lot_id} className="hover:bg-gray-50">
              {/* Lot ID links to the full detail page (AC2, AC9) */}
              <td className="px-4 py-2 font-medium text-blue-600 hover:underline">
                <Link to={`/lots/${row.lot_id}`}>{row.lot_id}</Link>
              </td>
              <td className="px-4 py-2">{dash(row.start_date)}</td>
              <td className="px-4 py-2">{dash(row.end_date)}</td>
              <td className="px-4 py-2 text-right">{dash(row.total_produced)}</td>
              <td className="px-4 py-2">{dash(row.lines_used)}</td>
              <td className="px-4 py-2 text-center">
                {row.any_issues === null
                  ? '—'
                  : row.any_issues
                    ? <span className="text-red-600 font-semibold">Yes</span>
                    : <span className="text-green-600">No</span>}
              </td>
              <td className="px-4 py-2 text-right">{dash(row.issue_count)}</td>
              <td className="px-4 py-2">{dash(row.latest_status)}</td>
              <td className="px-4 py-2 text-center">
                <CompletenessIndicator
                  score={Number(row.overall_completeness)}
                  hasProduction={Number(row.overall_completeness) > 0}
                  hasInspection={Number(row.overall_completeness) >= 67}
                  hasShipping={Number(row.overall_completeness) === 100}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
