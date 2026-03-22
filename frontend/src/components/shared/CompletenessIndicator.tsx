// src/components/shared/CompletenessIndicator.tsx
//
// Visual indicator showing a lot's data completeness score (0, 33, 67, or 100).
//
// Used in:
//   - LotSummaryTable (one per row)
//   - LotDetailPage (header section)
//   - IncompleteLotsTable (one per row)
//
// Supports AC4 (missing data visible) and AC10 (completeness score).

/**
 * Props for the CompletenessIndicator component.
 * All fields are required — the parent always has this data.
 */
interface CompletenessIndicatorProps {
  /** Overall completeness percentage. One of: 0, 33, 67, 100. */
  score: number;

  /** Whether individual domain flags are shown (for title tooltip). */
  hasProduction: boolean;
  hasInspection: boolean;
  hasShipping: boolean;
}

/**
 * CompletenessIndicator — displays a colored badge with the completeness score.
 *
 * Color coding:
 *   0%   → red    (no data at all)
 *   33%  → orange (one of three domains present)
 *   67%  → yellow (two of three domains present)
 *   100% → green  (all three domains present)
 *
 * A tooltip shows which individual domains are present/absent.
 *
 * @param props - score, hasProduction, hasInspection, hasShipping
 *
 * AC4:  Missing data is clearly visible via color and percentage.
 * AC10: Score is shown numerically.
 */
export default function CompletenessIndicator({
  score,
  hasProduction,
  hasInspection,
  hasShipping,
}: CompletenessIndicatorProps) {
  // ── Color class based on score value ────────────────────────────────────────
  const colorClass =
    score === 100
      ? 'bg-green-100 text-green-800'
      : score === 67
        ? 'bg-yellow-100 text-yellow-800'
        : score === 33
          ? 'bg-orange-100 text-orange-800'
          : 'bg-red-100 text-red-800'; // score === 0

  // ── Tooltip text shows per-domain status ────────────────────────────────────
  const domainStatus = [
    `Production: ${hasProduction ? '✓' : '✗'}`,
    `Inspection: ${hasInspection ? '✓' : '✗'}`,
    `Shipping: ${hasShipping ? '✓' : '✗'}`,
  ].join(' | ');

  return (
    <span
      className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${colorClass}`}
      title={domainStatus}
    >
      {score}%
    </span>
  );
}
