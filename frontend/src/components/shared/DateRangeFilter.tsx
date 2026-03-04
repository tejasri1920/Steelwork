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
   * The parent updates its state and passes the new values back via props.
   *
   * @param startDate - New start date value (ISO-8601 string or "").
   * @param endDate   - New end date value (ISO-8601 string or "").
   */
  onChange: (startDate: string, endDate: string) => void;
}

/**
 * DateRangeFilter — two date picker inputs for filtering lots by date range.
 *
 * Suggested structure:
 *   <div className="flex gap-4 items-center">
 *     <label>From: <input type="date" value={startDate} onChange={...} /></label>
 *     <label>To:   <input type="date" value={endDate}   onChange={...} /></label>
 *     <button onClick={() => onChange('', '')}>Clear</button>
 *   </div>
 *
 * @param props - startDate, endDate, onChange callback
 *
 * AC3: Used to filter the lots list by lots.start_date range.
 */
export default function DateRangeFilter(_props: DateRangeFilterProps) {
  // TODO: Render two date inputs and a Clear button.
  // Call props.onChange when either input value changes.
  throw new Error('TODO: Implement DateRangeFilter UI');
}
