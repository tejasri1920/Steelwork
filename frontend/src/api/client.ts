// src/api/client.ts
//
// Axios HTTP client and typed API functions.
//
// Architecture:
//   1. A single shared Axios instance (`apiClient`) is configured with:
//        - baseURL from VITE_API_BASE_URL env var (empty in Docker, set in local dev)
//        - default JSON content-type header
//   2. One typed function per API endpoint.
//      Each function uses `apiClient` to make the request and returns typed data.
//
// React Query calls these functions:
//   const { data } = useQuery({ queryKey: ['lots'], queryFn: () => fetchLots() });
//
// Error handling: Axios throws on non-2xx responses. React Query catches the error
// and exposes it via `error` in the hook result. Components render an error message.
//
// AC coverage:
//   AC2  — fetchLotByCode()
//   AC3  — fetchLots({ start_date, end_date })
//   AC4  — fetchIncompleteLots()
//   AC5  — fetchLineIssues()
//   AC6  — fetchInspectionIssues()
//   AC7  — fetchLotSummary()
//   AC8  — fetchLotSummary() (latest_status column)
//   AC9  — fetchLotByCode()
//   AC10 — fetchLots() + fetchIncompleteLots() (overall_completeness field)

import axios from 'axios';

import type {
  IncompleteLotRow,
  InspectionIssueRow,
  LineIssueRow,
  LotDetail,
  LotListParams,
  LotSummary,
  LotSummaryRow,
} from '../types';

// ── Axios instance ────────────────────────────────────────────────────────────

/**
 * Shared Axios instance used by all API functions.
 *
 * baseURL:
 *   - In Docker (Nginx proxy): VITE_API_BASE_URL = "" → requests go to the same origin.
 *     Nginx forwards /api/* to the FastAPI backend container.
 *   - In local dev (no Docker): VITE_API_BASE_URL = "http://localhost:8000".
 *     Vite dev server proxies /api/* to FastAPI (see vite.config.ts).
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
});


// ── Lot endpoints ─────────────────────────────────────────────────────────────

/**
 * Fetch all lots, optionally filtered by date range.
 *
 * Calls: GET /api/v1/lots/
 * Query params: start_date and end_date are optional ISO-8601 date strings.
 *
 * @param params - Optional date range filter (start_date, end_date).
 * @returns Array of LotSummary objects (may be empty if no lots match).
 *
 * AC3:  Date range filtering.
 * AC4/AC10: overall_completeness included in each row.
 */
export async function fetchLots(params?: LotListParams): Promise<LotSummary[]> {
  throw new Error(
    'TODO: apiClient.get<LotSummary[]>("/api/v1/lots/", { params }). ' +
    'Return response.data.'
  );
}

/**
 * Fetch full detail for a single lot by its lot_code.
 *
 * Calls: GET /api/v1/lots/{lotCode}
 * Throws AxiosError with status 404 if the lot does not exist.
 *
 * @param lotCode - Human-readable lot identifier, e.g. 'LOT-20260112-001'.
 * @returns LotDetail with all child records.
 *
 * AC2: Retrieve a specific lot.
 * AC9: Full drill-down including production, inspection, shipping records.
 */
export async function fetchLotByCode(lotCode: string): Promise<LotDetail> {
  throw new Error(
    'TODO: apiClient.get<LotDetail>(`/api/v1/lots/${lotCode}`). ' +
    'Return response.data.'
  );
}


// ── Report endpoints ──────────────────────────────────────────────────────────

/**
 * Fetch the aggregated lot summary report (one row per lot).
 *
 * Calls: GET /api/v1/reports/lot-summary
 * @returns Array of LotSummaryRow objects.
 *
 * AC1:  Cross-function view.
 * AC7:  Meeting-ready summary.
 * AC8:  latest_status shows shipment state.
 * AC10: overall_completeness per lot.
 */
export async function fetchLotSummary(): Promise<LotSummaryRow[]> {
  throw new Error(
    'TODO: apiClient.get<LotSummaryRow[]>("/api/v1/reports/lot-summary"). ' +
    'Return response.data.'
  );
}

/**
 * Fetch all lots with flagged inspections and their shipment status.
 *
 * Calls: GET /api/v1/reports/inspection-issues
 * @returns Array of InspectionIssueRow objects.
 *
 * AC5: Identify flagged lots.
 * AC6: Show shipment status for flagged lots.
 */
export async function fetchInspectionIssues(): Promise<InspectionIssueRow[]> {
  throw new Error(
    'TODO: apiClient.get<InspectionIssueRow[]>("/api/v1/reports/inspection-issues"). ' +
    'Return response.data.'
  );
}

/**
 * Fetch all lots missing production, inspection, or shipping data.
 *
 * Calls: GET /api/v1/reports/incomplete-lots
 * @returns Array of IncompleteLotRow objects, ordered most-incomplete first.
 *
 * AC4:  Surface incomplete lots.
 * AC10: Completeness score per lot.
 */
export async function fetchIncompleteLots(): Promise<IncompleteLotRow[]> {
  throw new Error(
    'TODO: apiClient.get<IncompleteLotRow[]>("/api/v1/reports/incomplete-lots"). ' +
    'Return response.data.'
  );
}

/**
 * Fetch issue counts and rates aggregated by production line.
 *
 * Calls: GET /api/v1/reports/line-issues
 * @returns Array of LineIssueRow objects, ordered by total_issues descending.
 *
 * AC5: Identify which lines have the highest issue rates.
 */
export async function fetchLineIssues(): Promise<LineIssueRow[]> {
  throw new Error(
    'TODO: apiClient.get<LineIssueRow[]>("/api/v1/reports/line-issues"). ' +
    'Return response.data.'
  );
}
