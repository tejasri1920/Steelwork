// postcss.config.js
//
// PostCSS plugin configuration.
//
// PostCSS processes CSS files, applying transformations defined by plugins.
// Vite automatically runs PostCSS on all CSS imports.
//
// Plugins used:
//   tailwindcss  — generates the Tailwind utility classes
//   autoprefixer — adds vendor prefixes (e.g. -webkit-) for browser compatibility

export default {
  plugins: {
    tailwindcss: {},    // Reads tailwind.config.js for configuration
    autoprefixer: {},   // Automatically adds browser vendor prefixes
  },
};
