// tests/CompletenessIndicator.test.tsx
//
// Unit tests for the CompletenessIndicator component.
//
// Tests verify that the component:
//   - Renders the correct score text
//   - Applies the correct color based on the score
//   - Renders correctly for all four possible score values (0, 33, 67, 100)
//
// AC4/AC10: Completeness score must be visually distinct and correct.

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

import CompletenessIndicator from '../src/components/shared/CompletenessIndicator';

describe('CompletenessIndicator', () => {

  it('displays the score as a percentage', () => {
    // Given a score of 100, the component should show "100%" in the DOM.
    // AC10: Completeness score is visible.
    throw new Error(
      'TODO: render CompletenessIndicator with score=100. ' +
      'expect(screen.getByText(/100/)).toBeInTheDocument().'
    );
  });

  it('renders for score=0 (no data)', () => {
    // A lot with no data at all should show 0%.
    throw new Error(
      'TODO: render CompletenessIndicator with score=0. ' +
      'assert the element is in the document.'
    );
  });

  it('renders for score=33 (one domain)', () => {
    // One of three domains present.
    throw new Error(
      'TODO: render CompletenessIndicator with score=33. ' +
      'assert the element is in the document.'
    );
  });

  it('renders for score=67 (two domains)', () => {
    // Two of three domains present.
    throw new Error(
      'TODO: render CompletenessIndicator with score=67. ' +
      'assert the element is in the document.'
    );
  });

});
