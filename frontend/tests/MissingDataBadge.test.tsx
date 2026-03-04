// tests/MissingDataBadge.test.tsx
//
// Unit tests for the MissingDataBadge component.
//
// Tests verify that the component:
//   - Renders nothing when hasDomain=true (domain is present)
//   - Renders a warning badge when hasDomain=false (domain is missing)
//   - Shows the correct domain name in the badge
//
// AC4: Missing data must be surfaced clearly — this component is the primary indicator.

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

import MissingDataBadge from '../src/components/shared/MissingDataBadge';

describe('MissingDataBadge', () => {

  it('renders nothing when hasDomain is true', () => {
    // If the domain has data, the badge should not appear.
    // AC4: Only missing domains are highlighted.
    throw new Error(
      'TODO: render MissingDataBadge with domain="production" hasDomain=true. ' +
      'assert the container is empty (no badge rendered).'
    );
  });

  it('renders a badge when hasDomain is false', () => {
    // If the domain is missing, a warning badge should appear.
    // AC4: Missing domain is visually indicated.
    throw new Error(
      'TODO: render MissingDataBadge with domain="inspection" hasDomain=false. ' +
      'expect(screen.getByText(/inspection/i)).toBeInTheDocument().'
    );
  });

  it('shows the correct domain name for shipping', () => {
    // Badge should reference the specific domain name.
    throw new Error(
      'TODO: render MissingDataBadge with domain="shipping" hasDomain=false. ' +
      'expect(screen.getByText(/shipping/i)).toBeInTheDocument().'
    );
  });

});
