// src/components/shared/IncompleteLotsTable.tsx
//
// Table showing lots that are missing production, inspection, or shipping data.
//
// Displayed on DashboardPage under the "Incomplete Lots" tab.
// Supports AC4 (surface missing data) and AC10 (completeness score).

import CompletenessIndicator from './CompletenessIndicator';
import MissingDataBadge from './MissingDataBadge';
import type { IncompleteLotRow } from '../../types';

/** Helper: render "—" for null/undefined values. */
const dash = (value: unknown) => (value === null || value === undefined ? '—' : String(value));

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
 * Columns:
 *   Lot ID | Start Date | End Date | Production | Inspection | Shipping | Completeness
 *
 * The Production/Inspection/Shipping columns show a MissingDataBadge when
 * the domain is absent, or a green check when it is present.
 *
 * @param props - rows from the incomplete-lots report endpoint
 *
 * AC4:  Analyst can identify which lots are missing data before a meeting.
 * AC10: Completeness score shown per row.
 */
export default function IncompleteLotsTable({ rows }: IncompleteLotsTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-green-600 text-sm py-4 font-medium">All lots are complete.</p>
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
            <th className="px-4 py-2 text-center">Production</th>
            <th className="px-4 py-2 text-center">Inspection</th>
            <th className="px-4 py-2 text-center">Shipping</th>
            <th className="px-4 py-2 text-center">Completeness</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row) => (
            <tr key={row.lot_id} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-medium">{row.lot_code}</td>
              <td className="px-4 py-2">{dash(row.start_date)}</td>
              <td className="px-4 py-2">{dash(row.end_date)}</td>
              <td className="px-4 py-2 text-center">
                {row.has_production_data
                  ? <span className="text-green-600">✓</span>
                  : <MissingDataBadge domain="production" hasDomain={false} />}
              </td>
              <td className="px-4 py-2 text-center">
                {row.has_inspection_data
                  ? <span className="text-green-600">✓</span>
                  : <MissingDataBadge domain="inspection" hasDomain={false} />}
              </td>
              <td className="px-4 py-2 text-center">
                {row.has_shipping_data
                  ? <span className="text-green-600">✓</span>
                  : <MissingDataBadge domain="shipping" hasDomain={false} />}
              </td>
              <td className="px-4 py-2 text-center">
                <CompletenessIndicator
                  score={Number(row.overall_completeness)}
                  hasProduction={row.has_production_data}
                  hasInspection={row.has_inspection_data}
                  hasShipping={row.has_shipping_data}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
