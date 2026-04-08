// src/pages/DashboardPage.tsx
//
// Main dashboard page — rendered at route "/".
//
// Contains four tabs, each showing a different analytical view:
//   Tab 1: "Summary"           → LotSummaryTable      (AC1, AC7, AC8, AC10)
//   Tab 2: "Inspection Issues" → InspectionIssuesTable (AC5, AC6)
//   Tab 3: "Line Issues"       → LineIssuesTable       (AC5)
//   Tab 4: "Incomplete Lots"   → IncompleteLotsTable   (AC4, AC10)
//
// A DateRangeFilter above the tabs is provided for analysts to filter the lots
// list endpoint (AC3). The four report tabs always show all data.
//
// AC coverage:
//   AC1  — Summary tab shows production + inspection + shipping side-by-side
//   AC3  — DateRangeFilter (wired to the lots list, not the reports)
//   AC4  — Incomplete Lots tab
//   AC5  — Inspection Issues tab + Line Issues tab
//   AC6  — Inspection Issues tab
//   AC7  — Summary tab (one row per lot)
//   AC8  — Summary tab (latest_status column)
//   AC10 — Summary tab + Incomplete Lots tab (completeness scores)

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  fetchIncompleteLots,
  fetchInspectionIssues,
  fetchLineIssues,
  fetchLotSummary,
} from '../api/client';

import DateRangeFilter from '../components/shared/DateRangeFilter';
import IncompleteLotsTable from '../components/shared/IncompleteLotsTable';
import InspectionIssuesTable from '../components/shared/InspectionIssuesTable';
import LineIssuesTable from '../components/shared/LineIssuesTable';
import LotSummaryTable from '../components/shared/LotSummaryTable';

/** Tab identifiers for the dashboard. */
type DashboardTab = 'summary' | 'inspection-issues' | 'line-issues' | 'incomplete-lots';

/** Tab metadata used to render the tab bar. */
const TABS: { id: DashboardTab; label: string }[] = [
  { id: 'summary', label: 'Lot Summary' },
  { id: 'inspection-issues', label: 'Inspection Issues' },
  { id: 'line-issues', label: 'Issues by Line' },
  { id: 'incomplete-lots', label: 'Incomplete Lots' },
];

/**
 * DashboardPage — main analytics view with tabbed reports.
 *
 * State:
 *   activeTab — which tab is currently displayed
 *   startDate — date filter lower bound (ISO-8601 string or "")
 *   endDate   — date filter upper bound (ISO-8601 string or "")
 *
 * React Query fetches all four reports eagerly so switching tabs is instant.
 */
export default function DashboardPage() {
  // ── Local state ─────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<DashboardTab>('summary');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // ── Data fetching ────────────────────────────────────────────────────────────
  // All four reports are fetched eagerly. React Query caches them, so switching
  // tabs doesn't cause extra network requests.
  const {
    data: summaryRows = [],
    isLoading: summaryLoading,
    error: summaryError,
  } = useQuery({
    queryKey: ['lot-summary', startDate, endDate],
    queryFn: () => fetchLotSummary({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
  });

  const {
    data: issueRows = [],
    isLoading: issuesLoading,
    error: issuesError,
  } = useQuery({ queryKey: ['inspection-issues'], queryFn: fetchInspectionIssues });

  const {
    data: lineRows = [],
    isLoading: lineLoading,
    error: lineError,
  } = useQuery({ queryKey: ['line-issues'], queryFn: fetchLineIssues });

  const {
    data: incompleteRows = [],
    isLoading: incompleteLoading,
    error: incompleteError,
  } = useQuery({ queryKey: ['incomplete-lots'], queryFn: fetchIncompleteLots });

  // ── Active tab data / state ──────────────────────────────────────────────────
  const tabState = {
    summary: { loading: summaryLoading, error: summaryError },
    'inspection-issues': { loading: issuesLoading, error: issuesError },
    'line-issues': { loading: lineLoading, error: lineError },
    'incomplete-lots': { loading: incompleteLoading, error: incompleteError },
  };
  const { loading, error } = tabState[activeTab];

  // ── Handlers ─────────────────────────────────────────────────────────────────
  const handleDateChange = (start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
  };

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Page title */}
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Operations Dashboard</h1>

      {/* Date range filter (AC3) — filters the Lot Summary tab by lot start_date */}
      <div className="bg-white border border-gray-200 rounded p-4 mb-6 flex flex-wrap items-center gap-4">
        <span className="text-sm font-medium text-gray-600">Filter lots by date:</span>
        <DateRangeFilter
          startDate={startDate}
          endDate={endDate}
          onChange={handleDateChange}
        />
      </div>

      {/* Tab bar — role="tablist" + role="tab" for proper ARIA semantics and
           Playwright get_by_role("tab") selectors in e2e tests. */}
      <div role="tablist" className="flex border-b border-gray-200 mb-6">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={activeTab === id}
            onClick={() => setActiveTab(id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-white border border-gray-200 rounded p-4">
        {loading && (
          <p className="text-gray-500 text-sm py-4">Loading…</p>
        )}

        {!loading && error && (
          <p className="text-red-600 text-sm py-4">
            Failed to load data. Please try refreshing the page.
          </p>
        )}

        {!loading && !error && (
          <>
            {activeTab === 'summary' && <LotSummaryTable rows={summaryRows} />}
            {activeTab === 'inspection-issues' && <InspectionIssuesTable rows={issueRows} />}
            {activeTab === 'line-issues' && <LineIssuesTable rows={lineRows} />}
            {activeTab === 'incomplete-lots' && <IncompleteLotsTable rows={incompleteRows} />}
          </>
        )}
      </div>
    </div>
  );
}
