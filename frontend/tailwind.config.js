// tailwind.config.js
//
// Tailwind CSS configuration.
//
// Tailwind generates utility classes (e.g. `text-lg`, `bg-blue-500`, `flex`)
// by scanning the files listed in `content`. Only classes actually used in
// those files are included in the production CSS bundle — unused classes are
// purged automatically.

/** @type {import('tailwindcss').Config} */
export default {
  // ── Content scanning ────────────────────────────────────────────────────────
  // Tailwind scans these files for class names to include in the CSS bundle.
  // Must include all files that use Tailwind classes.
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',    // All TypeScript and TSX source files
  ],

  theme: {
    extend: {
      // ── Custom colors ─────────────────────────────────────────────────────
      // Add project-specific colors here using Tailwind's extend pattern.
      // Example:
      //   colors: {
      //     steelworks: {
      //       blue: '#1a365d',
      //       steel: '#718096',
      //     },
      //   },
    },
  },

  plugins: [
    // Add Tailwind plugins here as needed, e.g.:
    // require('@tailwindcss/forms')   — styled form elements
    // require('@tailwindcss/typography') — prose / article styling
  ],
};
