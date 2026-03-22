// src/components/layout/Navbar.tsx
//
// Top navigation bar — visible on all pages.
//
// Contains:
//   - App title / brand (links back to the dashboard)
//   - Navigation links (Dashboard)
//
// Styled with Tailwind CSS utility classes.
// Uses React Router's <Link> for client-side navigation (no full page reload).

import { Link } from 'react-router-dom';

/**
 * Navbar — top-of-page navigation bar.
 *
 * Rendered by App.tsx outside <Routes> so it appears on every page.
 * Does not receive props — all content is static.
 */
export default function Navbar() {
  return (
    <nav className="bg-gray-800 text-white px-6 py-4 flex items-center gap-8 shadow-md">
      {/* Brand / home link */}
      <Link to="/" className="text-xl font-bold tracking-tight hover:text-gray-200">
        Steelworks Ops
      </Link>

      {/* Navigation links */}
      <Link to="/" className="text-sm text-gray-300 hover:text-white hover:underline">
        Dashboard
      </Link>
    </nav>
  );
}
