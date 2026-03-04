// src/pages/DashboardPage.tsx
//
// Main dashboard page — rendered at route "/".
//
// Contains four tabs, each showing a different analytical view:
//   Tab 1: "Summary"          → LotSummaryTable     (AC1, AC7, AC8, AC10)
//   Tab 2: "Inspection Issues"→ InspectionIssuesTable (AC5, AC6)
//   Tab 3: "Line Issues"      → LineIssuesTable      (AC5)
//   Tab 4: "Incomplete Lots"  → IncompleteLotsTable  (AC4, AC10)
//
// A DateRangeFilter above the tabs filters the lots list (not the reports).
//
// Data fetching:
//   All four reports are fetched via React Query's useQuery.
//   React Query caches results and shows loading/error states automatically.
//
// AC coverage on this page:
//   AC1  — Summary tab shows production + inspection + shipping side-by-side
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

/**
 * DashboardPage — main analytics view with tabbed reports.
 *
 * State:
 *   activeTab   — which tab is currently displayed
 *   startDate   — date filter lower bound (ISO-8601 string or "")
 *   endDate     — date filter upper bound (ISO-8601 string or "")
 *
 * React Query hooks:
 *   useLotSummary         — fetches /api/v1/reports/lot-summary
 *   useInspectionIssues   — fetches /api/v1/reports/inspection-issues
 *   useLineIssues         — fetches /api/v1/reports/line-issues
 *   useIncompleteLots     — fetches /api/v1/reports/incomplete-lots
 *
 * Note: The date filter applies to the lots list endpoint, not the reports.
 * The reports always return all data. Date filtering is shown in the lots list
 * which can be accessed via the LotSummaryTable row links.
 */
export default function DashboardPage() {
  // TODO: Implement DashboardPage.
  //
  // 1. Declare state:
  //    const [activeTab, setActiveTab] = useState<DashboardTab>('summary');
  //    const [startDate, setStartDate] = useState('');
  //    const [endDate, setEndDate] = useState('');
  //
  // 2. Fetch all four reports with useQuery:
  //    const { data: summaryRows, isLoading, error } = useQuery({
  //      queryKey: ['lot-summary'],
  //      queryFn: fetchLotSummary,
  //    });
  //    (same pattern for the other three reports)
  //
  // 3. Render:
  //    - Page title ("Operations Dashboard")
  //    - DateRangeFilter (for the lots list, not the reports)
  //    - Tab bar (4 tabs)
  //    - Active tab content (one of the four table components)
  //    - Loading spinner when isLoading=true
  //    - Error message when error is set
  throw new Error('TODO: Implement DashboardPage');
}
