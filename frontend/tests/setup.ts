// tests/setup.ts
//
// Vitest global test setup file.
//
// This file is run before every test file (configured in vite.config.ts:
//   test.setupFiles: ['./tests/setup.ts']).
//
// What it does:
//   Imports @testing-library/jest-dom which extends Vitest's `expect` with
//   DOM-specific matchers like:
//     .toBeInTheDocument()  — element is rendered in the DOM
//     .toHaveTextContent()  — element contains specific text
//     .toBeDisabled()       — form element is disabled
//     .toHaveClass()        — element has a specific CSS class
//
// Without this import, those matchers would be undefined and tests would fail
// with "toBeInTheDocument is not a function".

import '@testing-library/jest-dom';
