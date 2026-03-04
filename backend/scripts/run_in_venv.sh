#!/usr/bin/env bash
#
# backend/scripts/run_in_venv.sh
#
# Wrapper used by .pre-commit-config.yaml hooks.
# Runs a command from the backend/ directory using the project's Poetry virtualenv.
#
# Usage (called by pre-commit from the repo root):
#   bash backend/scripts/run_in_venv.sh <tool> [args...]
#
# Resolution order for the tool executable:
#   1. PATH — succeeds in CI after the workflow adds the venv bin/ to GITHUB_PATH.
#   2. Poetry venv discovered via `poetry env list --full-path` — works on Windows
#      when the venv's Scripts/ dir is not on the system PATH.
#
# Time complexity:  O(1) — one `command -v` check, at most one `poetry env list`.
# Space complexity: O(1) — no collections, just scalar variables.

set -euo pipefail

# ── Locate the backend/ directory ─────────────────────────────────────────────
# BASH_SOURCE[0] is this script's path; go up one level from scripts/ to backend/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# All hooks must run from backend/ so that:
#   - ruff reads config from backend/pyproject.toml
#   - mypy resolves `app/` relative to backend/
#   - pytest finds backend/tests/
cd "$BACKEND_DIR"

# ── Extract the tool name and its arguments ────────────────────────────────────
TOOL="$1"
shift
ARGS=("$@")

# ── 1. Try PATH first (CI scenario) ───────────────────────────────────────────
if command -v "$TOOL" &>/dev/null; then
    exec "$TOOL" "${ARGS[@]}"
fi

# ── 2. Discover Poetry virtualenv (local Windows scenario) ────────────────────
if command -v poetry &>/dev/null; then
    # `poetry env list --full-path` prints the venv path(s) for this project.
    # On Windows the path uses backslashes — tr converts them for bash.
    VENV="$(poetry env list --full-path 2>/dev/null | head -1 | awk '{print $1}' | tr '\\' '/')"

    if [ -n "$VENV" ]; then
        # Try Windows-style Scripts/ first, then Unix-style bin/
        for BIN in "$VENV/Scripts/$TOOL" "$VENV/Scripts/${TOOL}.exe" "$VENV/bin/$TOOL"; do
            if [ -f "$BIN" ]; then
                exec "$BIN" "${ARGS[@]}"
            fi
        done
    fi
fi

# ── Failure ───────────────────────────────────────────────────────────────────
echo "ERROR: '$TOOL' not found in PATH or Poetry virtualenv." >&2
echo "  Run: pip install pre-commit && pre-commit install" >&2
exit 1
