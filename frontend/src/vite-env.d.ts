/// <reference types="vite/client" />
//
// vite-env.d.ts — Vite environment type declarations.
//
// This file tells TypeScript about Vite-specific globals:
//   - `import.meta.env`  — access to environment variables (VITE_* prefix)
//   - `import.meta.hot`  — hot module replacement API
//
// Without this reference, TypeScript will report:
//   "Property 'env' does not exist on type 'ImportMeta'"
//
// Typed env variables are declared in the `ImportMetaEnv` interface below.
// Only VITE_* prefixed variables are exposed to the browser (Vite strips others).

interface ImportMetaEnv {
  /**
   * Base URL for API calls.
   * - In Docker (Nginx proxy): empty string "" — Nginx forwards /api/* to backend.
   * - In local dev (no Docker): "http://localhost:8000" — direct connection to FastAPI.
   * Set in .env or .env.example as VITE_API_BASE_URL.
   */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
