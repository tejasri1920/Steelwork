// src/components/shared/MissingDataBadge.tsx
//
// Small badge that highlights a specific missing data domain for a lot.
//
// Used in IncompleteLotsTable to show which specific domain is missing
// (production, inspection, or shipping) per lot row.
//
// Supports AC4 (surface missing data clearly).

/**
 * Props for the MissingDataBadge component.
 */
interface MissingDataBadgeProps {
  /**
   * Which data domain this badge represents.
   * The badge is only rendered when the domain is missing (hasDomain=false).
   */
  domain: 'production' | 'inspection' | 'shipping';

  /**
   * Whether this domain has data.
   * If true, the badge renders nothing (domain is complete).
   * If false, the badge renders a warning indicator.
   */
  hasDomain: boolean;
}

/**
 * MissingDataBadge — renders a warning badge if the domain is missing.
 *
 * Returns null (renders nothing) when hasDomain is true.
 * Returns a small red pill badge when hasDomain is false.
 *
 * @param props - domain name, hasDomain flag
 *
 * AC4: Visually highlights which data domain is absent for a lot.
 */
export default function MissingDataBadge({ domain, hasDomain }: MissingDataBadgeProps) {
  // Data is present — render nothing so the cell stays clean.
  if (hasDomain) return null;

  // Data is missing — show a compact warning pill.
  return (
    <span className="inline-block bg-red-100 text-red-700 text-xs font-medium px-2 py-0.5 rounded-full">
      No {domain}
    </span>
  );
}
