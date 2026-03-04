// src/main.tsx
//
// Application bootstrap — the entry point that Vite loads first.
//
// Responsibilities:
//   1. Import global CSS (Tailwind directives).
//   2. Wrap the App in React Query's QueryClientProvider so all
//      components can call `useQuery` and `useMutation`.
//   3. Wrap the App in BrowserRouter so all components can use
//      React Router's hooks (useNavigate, useParams, Link, etc.).
//   4. Mount the root React component into the #root div in index.html.
//
// Why React Query?
//   React Query handles server state (API data): caching, background refetch,
//   loading and error states. This keeps components clean — they just call
//   `useQuery(...)` instead of managing useState + useEffect manually.
//
// Why BrowserRouter?
//   Enables client-side routing (navigation without full page reloads).
//   Routes are defined in App.tsx.

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import './index.css';   // Global Tailwind CSS

// ── React Query client ────────────────────────────────────────────────────────
// QueryClient holds the cache for all server-state queries.
// Default options can be configured here (e.g. staleTime, retry count).
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 30 seconds — no background refetch within this window.
      // Adjust per query in individual useQuery() calls if needed.
      staleTime: 30_000,

      // Retry failed queries up to 1 time before showing an error.
      retry: 1,
    },
  },
});

// ── Mount the app ─────────────────────────────────────────────────────────────
// ReactDOM.createRoot is the React 18 API (replaces ReactDOM.render).
// document.getElementById('root')! — the ! asserts the element exists (see index.html).
ReactDOM.createRoot(document.getElementById('root')!).render(
  // StrictMode renders components twice in development to surface side-effect bugs.
  // Has no effect in production.
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
