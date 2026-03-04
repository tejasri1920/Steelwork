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
 *
 * Suggested styling: small red or orange pill with the domain name.
 *   Example: <span className="bg-red-100 text-red-700 text-xs px-2 py-1 rounded">
 *               No {domain}
 *            </span>
 *
 * @param props - domain name, hasDomain flag
 */
export default function MissingDataBadge(_props: MissingDataBadgeProps) {
  // TODO: If hasDomain is true, return null.
  // Otherwise, render a small warning badge with the domain name.
  throw new Error('TODO: Implement MissingDataBadge UI');
}
