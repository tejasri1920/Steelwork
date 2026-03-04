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
// Data fetching:
//   Uses useParams() to extract lotCode from the URL.
//   Uses useQuery() to fetch the full LotDetail from GET /api/v1/lots/{lotCode}.
//   Shows a loading spinner while fetching and an error/404 message if not found.
//
// AC coverage on this page:
//   AC2  — user navigated here by lot_code (from a link on the dashboard)
//   AC9  — full drill-down: all three child record types displayed

import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { fetchLotByCode } from '../api/client';
import CompletenessIndicator from '../components/shared/CompletenessIndicator';

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
 *   - Loading state
 *   - 404 state if lot not found
 *   - Generic error state
 *
 * AC2: Accessed by lot_code from the dashboard.
 * AC9: Shows all child record types in one view.
 */
export default function LotDetailPage() {
  // TODO: Implement LotDetailPage.
  //
  // 1. Extract lotCode from URL:
  //    const { lotCode } = useParams<{ lotCode: string }>();
  //
  // 2. Fetch lot detail:
  //    const { data: lot, isLoading, error } = useQuery({
  //      queryKey: ['lot', lotCode],
  //      queryFn: () => fetchLotByCode(lotCode!),
  //      enabled: !!lotCode,  // Don't fetch if lotCode is undefined
  //    });
  //
  // 3. Handle loading:
  //    if (isLoading) return <div>Loading...</div>;
  //
  // 4. Handle 404 / error:
  //    Check if error is an AxiosError with status 404.
  //    If so, show "Lot not found" message.
  //    Otherwise show a generic error message.
  //
  // 5. Render lot detail:
  //    - <Link to="/">← Back to Dashboard</Link>
  //    - Lot header: lot_code, start_date, end_date
  //    - CompletenessIndicator (score, hasProduction, hasInspection, hasShipping)
  //    - Production records: table with all ProductionRecord fields
  //    - Inspection records: table with all InspectionRecord fields
  //    - Shipping records: table with all ShippingRecord fields
  //    - Each table shows "No [type] records" when the array is empty
  throw new Error('TODO: Implement LotDetailPage');
}
