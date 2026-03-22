// src/pages/LotDetailPage.tsx
//
// Lot detail page — rendered at route "/lots/:lotCode".
//
// Shows all data for a single lot:
//   - Lot header (lot_code, dates, completeness score)
//   - Production records table
//   - Inspection records table
//   - Shipping records table
//
// AC coverage:
//   AC2  — user navigated here by lot_code (from a link on the dashboard)
//   AC9  — full drill-down: all three child record types displayed

import axios from 'axios';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { fetchLotByCode } from '../api/client';
import CompletenessIndicator from '../components/shared/CompletenessIndicator';
import type { InspectionRecord, ProductionRecord, ShippingRecord } from '../types';

/** Helper: render "—" for null/undefined values. */
const dash = (value: unknown) => (value === null || value === undefined ? '—' : String(value));

/**
 * LotDetailPage — full drill-down view for a single lot.
 *
 * URL parameter:
 *   lotCode — extracted from the route "/lots/:lotCode" via useParams().
 *
 * Renders:
 *   - Back link to the dashboard
 *   - Lot header card (lot_code, dates, completeness score)
 *   - Production records table
 *   - Inspection records table
 *   - Shipping records table
 *   - Loading, 404, and generic error states
 *
 * AC2: Accessed by lot_code from the dashboard.
 * AC9: Shows all child record types in one view.
 */
export default function LotDetailPage() {
  const { lotCode } = useParams<{ lotCode: string }>();

  const { data: lot, isLoading, error } = useQuery({
    queryKey: ['lot', lotCode],
    queryFn: () => fetchLotByCode(lotCode!),
    enabled: !!lotCode,  // Skip fetch if lotCode is somehow undefined
    retry: (failureCount, err) => {
      // Don't retry 404s — the lot simply doesn't exist.
      if (axios.isAxiosError(err) && err.response?.status === 404) return false;
      return failureCount < 1;
    },
  });

  // ── Loading state ────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <p className="text-gray-500">Loading lot detail…</p>
      </div>
    );
  }

  // ── Error / 404 state ────────────────────────────────────────────────────────
  if (error) {
    const is404 = axios.isAxiosError(error) && error.response?.status === 404;
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <Link to="/" className="text-blue-600 hover:underline text-sm">← Back to Dashboard</Link>
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded text-red-700">
          {is404
            ? `Lot "${lotCode}" was not found.`
            : 'Failed to load lot detail. Please try again.'}
        </div>
      </div>
    );
  }

  if (!lot) return null;

  // ── Lot detail render ────────────────────────────────────────────────────────
  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Back navigation */}
      <Link to="/" className="text-blue-600 hover:underline text-sm">← Back to Dashboard</Link>

      {/* Lot header card */}
      <div className="bg-white border border-gray-200 rounded p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{lot.lot_code}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Start: {lot.start_date} &nbsp;|&nbsp; End: {dash(lot.end_date)}
            </p>
          </div>
          <CompletenessIndicator
            score={Number(lot.overall_completeness)}
            hasProduction={lot.has_production_data}
            hasInspection={lot.has_inspection_data}
            hasShipping={lot.has_shipping_data}
          />
        </div>
        <div className="mt-3 flex gap-4 text-xs text-gray-400">
          <span>Created: {new Date(lot.created_at).toLocaleDateString()}</span>
          <span>Updated: {new Date(lot.updated_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Production records (AC9) */}
      <Section title="Production Records" count={lot.production_records.length}>
        {lot.production_records.length === 0 ? (
          <EmptyMessage>No production records.</EmptyMessage>
        ) : (
          <table className="min-w-full text-sm border border-gray-200 rounded">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-3 py-2 text-left">Date</th>
                <th className="px-3 py-2 text-left">Line</th>
                <th className="px-3 py-2 text-right">Qty Produced</th>
                <th className="px-3 py-2 text-right">Planned</th>
                <th className="px-3 py-2 text-left">Shift</th>
                <th className="px-3 py-2 text-left">Part #</th>
                <th className="px-3 py-2 text-right">Downtime (min)</th>
                <th className="px-3 py-2 text-center">Issue</th>
                <th className="px-3 py-2 text-left">Primary Issue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lot.production_records.map((p: ProductionRecord) => (
                <tr key={p.production_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">{p.production_date}</td>
                  <td className="px-3 py-2">{p.production_line}</td>
                  <td className="px-3 py-2 text-right">{p.quantity_produced}</td>
                  <td className="px-3 py-2 text-right">{p.units_planned}</td>
                  <td className="px-3 py-2">{p.shift}</td>
                  <td className="px-3 py-2">{p.part_number}</td>
                  <td className="px-3 py-2 text-right">{p.downtime_min}</td>
                  <td className="px-3 py-2 text-center">
                    {p.line_issue
                      ? <span className="text-red-600 font-semibold">Yes</span>
                      : <span className="text-green-600">No</span>}
                  </td>
                  <td className="px-3 py-2">{dash(p.primary_issue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {/* Inspection records (AC9, AC5) */}
      <Section title="Inspection Records" count={lot.inspection_records.length}>
        {lot.inspection_records.length === 0 ? (
          <EmptyMessage>No inspection records.</EmptyMessage>
        ) : (
          <table className="min-w-full text-sm border border-gray-200 rounded">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-3 py-2 text-left">Date</th>
                <th className="px-3 py-2 text-left">Inspector</th>
                <th className="px-3 py-2 text-left">Result</th>
                <th className="px-3 py-2 text-center">Issue Flag</th>
                <th className="px-3 py-2 text-left">Category</th>
                <th className="px-3 py-2 text-right">Defects</th>
                <th className="px-3 py-2 text-right">Sample Size</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lot.inspection_records.map((i: InspectionRecord) => (
                <tr
                  key={i.inspection_id}
                  className={i.issue_flag ? 'bg-red-50 hover:bg-red-100' : 'hover:bg-gray-50'}
                >
                  <td className="px-3 py-2">{i.inspection_date}</td>
                  <td className="px-3 py-2">{i.inspector_id}</td>
                  <td className="px-3 py-2">
                    <span className={i.inspection_result === 'Fail' ? 'text-red-600 font-semibold' : ''}>
                      {i.inspection_result}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {i.issue_flag
                      ? <span className="text-red-600 font-semibold">Yes</span>
                      : <span className="text-green-600">No</span>}
                  </td>
                  <td className="px-3 py-2">{dash(i.issue_category)}</td>
                  <td className="px-3 py-2 text-right">{i.defect_count}</td>
                  <td className="px-3 py-2 text-right">{i.sample_size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {/* Shipping records (AC9, AC6, AC8) */}
      <Section title="Shipping Records" count={lot.shipping_records.length}>
        {lot.shipping_records.length === 0 ? (
          <EmptyMessage>No shipping records.</EmptyMessage>
        ) : (
          <table className="min-w-full text-sm border border-gray-200 rounded">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-3 py-2 text-left">Ship Date</th>
                <th className="px-3 py-2 text-left">Carrier</th>
                <th className="px-3 py-2 text-left">Tracking #</th>
                <th className="px-3 py-2 text-left">Destination</th>
                <th className="px-3 py-2 text-right">Qty Shipped</th>
                <th className="px-3 py-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lot.shipping_records.map((s: ShippingRecord) => (
                <tr key={s.shipping_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">{s.ship_date}</td>
                  <td className="px-3 py-2">{s.carrier}</td>
                  <td className="px-3 py-2">{dash(s.tracking_number)}</td>
                  <td className="px-3 py-2">{s.destination}</td>
                  <td className="px-3 py-2 text-right">{s.quantity_shipped}</td>
                  <td className="px-3 py-2">
                    <span className={s.shipment_status === 'On Hold' ? 'text-red-600 font-semibold' : ''}>
                      {s.shipment_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  );
}

// ── Small layout helpers ──────────────────────────────────────────────────────

/** Wraps a child record section with a heading and record count badge. */
function Section({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded p-5">
      <h2 className="text-lg font-semibold text-gray-700 mb-3 flex items-center gap-2">
        {title}
        <span className="text-xs font-normal bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
          {count} record{count !== 1 ? 's' : ''}
        </span>
      </h2>
      <div className="overflow-x-auto">{children}</div>
    </div>
  );
}

/** Empty-state message for a section with no records. */
function EmptyMessage({ children }: { children: React.ReactNode }) {
  return <p className="text-gray-400 text-sm py-2">{children}</p>;
}
