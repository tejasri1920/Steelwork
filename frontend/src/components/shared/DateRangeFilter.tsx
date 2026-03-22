// src/components/shared/DateRangeFilter.tsx
//
// Date range filter control — two date inputs (start and end).
//
// Used in DashboardPage to filter the lots list by date range (AC3).
// The parent component holds the filter state and passes it down via props.
//
// This is a "controlled" component — it does not manage its own state.
// The parent provides current values and an onChange callback.
//
// Supports AC3 (date range filtering on lots.start_date).

/**
 * Props for the DateRangeFilter component.
 */
interface DateRangeFilterProps {
  /** Current start date value (ISO-8601 string, e.g. "2026-01-01"), or empty string. */
  startDate: string;

  /** Current end date value (ISO-8601 string, e.g. "2026-01-31"), or empty string. */
  endDate: string;

  /**
   * Called when either date input changes.
   * @param startDate - New start date value (ISO-8601 string or "").
   * @param endDate   - New end date value (ISO-8601 string or "").
   */
  onChange: (startDate: string, endDate: string) => void;
}

/**
 * DateRangeFilter — two date picker inputs for filtering lots by date range.
 *
 * Each input fires onChange immediately on change so the parent can re-fetch.
 * The Clear button resets both values to empty strings.
 *
 * @param props - startDate, endDate, onChange callback
 *
 * AC3: Used to filter the lots list by lots.start_date range.
 */
export default function DateRangeFilter({ startDate, endDate, onChange }: DateRangeFilterProps) {
  return (
    <div className="flex flex-wrap gap-4 items-center">
      <label className="flex items-center gap-2 text-sm text-gray-700">
        From
        <input
          type="date"
          value={startDate}
          onChange={(e) => onChange(e.target.value, endDate)}
          className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </label>

      <label className="flex items-center gap-2 text-sm text-gray-700">
        To
        <input
          type="date"
          value={endDate}
          onChange={(e) => onChange(startDate, e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </label>

      {/* Clear button — only shown when a filter is active to reduce visual noise. */}
      {(startDate || endDate) && (
        <button
          onClick={() => onChange('', '')}
          className="text-sm text-gray-500 hover:text-gray-800 underline"
        >
          Clear
        </button>
      )}
    </div>
  );
}
