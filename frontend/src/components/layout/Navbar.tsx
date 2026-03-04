// src/components/layout/Navbar.tsx
//
// Top navigation bar — visible on all pages.
//
// Contains:
//   - App title / brand (links back to the dashboard)
//   - Navigation links (Dashboard, and any future top-level pages)
//
// Styled with Tailwind CSS utility classes.
// Uses React Router's <Link> for client-side navigation (no full page reload).

import { Link } from 'react-router-dom';

/**
 * Navbar — top-of-page navigation bar.
 *
 * Rendered by App.tsx outside <Routes> so it appears on every page.
 * Does not receive props — all data is static (nav links, app name).
 */
export default function Navbar() {
  // TODO: Implement the navbar UI.
  // Suggested structure:
  //   <nav className="bg-gray-800 text-white px-6 py-4 flex items-center gap-8">
  //     <Link to="/" className="text-xl font-bold">Steelworks Ops</Link>
  //     <Link to="/" className="hover:underline">Dashboard</Link>
  //   </nav>
  throw new Error('TODO: Implement Navbar UI');
}
