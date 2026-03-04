# frontend/Dockerfile
#
# Two-stage build for the React frontend.
#
# Stage 1 (builder): Installs npm dependencies and runs `npm run build`.
#   Output: static files in /app/dist (HTML, JS bundles, CSS, assets).
#
# Stage 2 (runtime): Copies the static files into an Nginx image.
#   Nginx serves the static files and proxies /api/* to the FastAPI backend.
#
# Why two stages?
#   The builder stage needs Node.js and all dev dependencies (~500MB).
#   The runtime stage only needs the compiled static files served by Nginx (~50MB).
#   Multi-stage builds keep the final image small by discarding the build toolchain.

# ── Stage 1: Build ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first (before source code) so Docker can cache the
# npm install layer. If only source files change, npm install is skipped.
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies needed for the build)
RUN npm ci

# Copy the rest of the source code
COPY . .

# Run the production build.
# tsc checks types; vite build compiles and bundles into /app/dist
RUN npm run build

# ── Stage 2: Serve ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Copy the compiled static files from the builder stage into Nginx's default serve directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom Nginx config that adds the /api/* proxy rule
# (overwrites the default Nginx config)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Nginx listens on port 80 by default
EXPOSE 80

# Default CMD from nginx:alpine image starts Nginx in foreground mode
# CMD ["nginx", "-g", "daemon off;"]
