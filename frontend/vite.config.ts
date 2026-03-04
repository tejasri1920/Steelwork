// vite.config.ts
//
// Vite build tool configuration.
//
// Vite is the build tool and dev server for the React frontend.
// This config does three things:
//   1. Enables React JSX/TSX compilation via the @vitejs/plugin-react plugin.
//   2. Configures a dev server proxy so that requests to /api/* during development
//      are forwarded to the FastAPI backend (avoids CORS issues during local dev).
//   3. Configures Vitest for unit testing (testEnvironment: 'jsdom' simulates a browser).
//
// In production (Docker), Nginx handles the /api/* proxy instead of this config.
// This proxy is only active when running `npm run dev`.

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    // @vitejs/plugin-react enables Fast Refresh (instant feedback on edits)
    // and compiles JSX/TSX to JavaScript.
    react(),
  ],

  server: {
    // Dev server port — matches VITE_API_BASE_URL in .env.example
    port: 5173,

    proxy: {
      // Forward any request starting with /api to the FastAPI backend.
      // This mirrors the Nginx proxy_pass configuration used in production.
      // Without this, the browser would block cross-origin requests.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,   // Rewrites the Host header to match the target
      },
    },
  },

  // ── Vitest configuration ────────────────────────────────────────────────────
  // Vitest reads this section when you run `npm run test` or `vitest`.
  test: {
    // 'jsdom' provides a simulated browser environment (window, document, etc.)
    // Required for testing React components that manipulate the DOM.
    environment: 'jsdom',

    // Automatically import jest-dom matchers (e.g. `expect(...).toBeInTheDocument()`)
    // in every test file without needing to import them manually.
    setupFiles: ['./tests/setup.ts'],

    // Show coverage from all source files, not just those imported by tests.
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/main.tsx', 'src/vite-env.d.ts'],
    },
  },
});
