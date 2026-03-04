// tests/DateRangeFilter.test.tsx
//
// Unit tests for the DateRangeFilter component.
//
// Tests verify that the component:
//   - Renders start and end date inputs
//   - Calls onChange when an input value changes
//   - Calls onChange with empty strings when Clear is clicked
//
// AC3: Date range filter inputs must work correctly for the analyst to filter lots.

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import DateRangeFilter from '../src/components/shared/DateRangeFilter';

describe('DateRangeFilter', () => {

  it('renders start date and end date inputs', () => {
    // The component should render two date pickers.
    // AC3: Both bounds of the date range must be settable.
    throw new Error(
      'TODO: render DateRangeFilter with startDate="" endDate="" onChange={vi.fn()}. ' +
      'assert two date inputs are in the document.'
    );
  });

  it('calls onChange when start date changes', () => {
    // When the user changes the start date, onChange should be called.
    // AC3: Filter triggers when date is selected.
    throw new Error(
      'TODO: const onChange = vi.fn(). ' +
      'render DateRangeFilter. ' +
      'fireEvent.change(startDateInput, { target: { value: "2026-01-01" } }). ' +
      'expect(onChange).toHaveBeenCalled().'
    );
  });

  it('calls onChange with empty strings when Clear is clicked', () => {
    // Clicking Clear should reset both date inputs.
    // AC3: Analyst can clear the filter to see all lots.
    throw new Error(
      'TODO: const onChange = vi.fn(). ' +
      'render DateRangeFilter with startDate="2026-01-01" endDate="2026-01-31". ' +
      'fireEvent.click(clearButton). ' +
      'expect(onChange).toHaveBeenCalledWith("", "").'
    );
  });

});
