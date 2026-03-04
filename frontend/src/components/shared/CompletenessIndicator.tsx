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

  /** Whether individual domain flags are shown (optional tooltip/detail). */
  hasProduction: boolean;
  hasInspection: boolean;
  hasShipping: boolean;
}

/**
 * CompletenessIndicator — displays a colored badge with the completeness score.
 *
 * Color coding (suggested):
 *   0%   → red background (no data at all)
 *   33%  → orange background (one of three domains present)
 *   67%  → yellow background (two of three domains present)
 *   100% → green background (all three domains present)
 *
 * @param props - score, hasProduction, hasInspection, hasShipping
 */
export default function CompletenessIndicator(_props: CompletenessIndicatorProps) {
  // TODO: Implement completeness indicator UI.
  // Suggested structure:
  //   <span className={colorClass}>
  //     {score}%
  //   </span>
  // Where colorClass is determined by the score value.
  throw new Error('TODO: Implement CompletenessIndicator UI');
}
