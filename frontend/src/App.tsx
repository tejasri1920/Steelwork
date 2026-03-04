// src/App.tsx
//
// Root application component — defines the route structure.
//
// React Router v6 uses a declarative <Routes> / <Route> tree to map
// URL paths to page components. When the URL changes, React Router
// renders the matching <Route>'s element without a full page reload.
//
// Route structure:
//   /            → DashboardPage  (tab view: summary, issues, incomplete lots)
//   /lots/:lotCode → LotDetailPage  (full drill-down for one lot)
//   *            → 404 fallback
//
// The Navbar is rendered outside <Routes> so it appears on every page.
// Page components are responsible for their own data fetching via React Query.

import { Routes, Route } from 'react-router-dom';

import Navbar from './components/layout/Navbar';
import DashboardPage from './pages/DashboardPage';
import LotDetailPage from './pages/LotDetailPage';

/**
 * App — root component that defines the navigation structure.
 *
 * Rendered by main.tsx inside QueryClientProvider and BrowserRouter.
 * All routes are relative to the app root (/).
 */
export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar is fixed at the top — visible on all pages */}
      <Navbar />

      {/* Main content area — padded to avoid overlap with the navbar */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Routes>
          {/* Dashboard: summary tables, inspection issues, incomplete lots */}
          <Route path="/" element={<DashboardPage />} />

          {/* Lot detail: full drill-down by lot_code (e.g. /lots/LOT-20260112-001) */}
          <Route path="/lots/:lotCode" element={<LotDetailPage />} />

          {/* 404 fallback — catches all unmatched routes */}
          <Route
            path="*"
            element={
              <div className="text-center py-16">
                <h2 className="text-2xl font-semibold text-gray-700">404 — Page not found</h2>
                <p className="mt-2 text-gray-500">The page you requested does not exist.</p>
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
