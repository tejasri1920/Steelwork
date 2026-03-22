#!/usr/bin/env python3
"""
backend/scripts/check_gpl_licenses.py

Pre-commit helper: scan every package installed in the active virtualenv and
fail if any carries a copyleft license (GPL / AGPL / LGPL).

Why copyleft matters:
    GPL, AGPL, and LGPL licenses impose "share-alike" conditions.  Bundling
    a copyleft dependency into a proprietary application can require releasing
    the entire application's source code under the same license.  Catching
    these early (at commit time) prevents legal surprises at release.

Usage (called by .pre-commit-config.yaml via run_in_venv.sh):
    python scripts/check_gpl_licenses.py

Exit codes:
    0 — all licenses are permissive (MIT, Apache-2.0, BSD, PSF, etc.)
    1 — one or more copyleft licenses detected

Time complexity:  O(n) — one pass over the list of installed packages.
Space complexity: O(n) — stores the full package list in memory.
"""

import json
import os
import subprocess
import sys

# ── License prefixes that trigger a block ─────────────────────────────────────
# We match by prefix so that "GPL-2.0-only", "GPLv3+", "LGPL-2.1", etc.
# are all caught by a single short string comparison.
COPYLEFT_PREFIXES: tuple[str, ...] = ("GPL", "AGPL", "LGPL")


def _pip_licenses_executable() -> str:
    """
    Resolve the ``pip-licenses`` executable that lives in the same virtualenv
    as the running Python interpreter.

    Why not rely on PATH?
        pre-commit invokes this script via ``run_in_venv.sh``, which passes the
        *venv's Python* as the interpreter but does NOT add the venv's Scripts/
        directory to PATH.  Using ``sys.executable`` as the anchor guarantees
        we always find the ``pip-licenses`` that belongs to the active venv,
        regardless of what the shell's PATH contains.

    Resolution order (same directory as sys.executable):
        1. ``pip-licenses``         — Linux / macOS venv bin/
        2. ``pip-licenses.exe``     — Windows venv Scripts/

    Raises:
        FileNotFoundError: if neither candidate exists.

    Time complexity:  O(1)
    Space complexity: O(1)
    """
    # sys.executable is e.g. /path/to/venv/bin/python  or
    #                         C:\\...\\venv\\Scripts\\python.exe
    venv_bin = os.path.dirname(sys.executable)

    for candidate in ("pip-licenses", "pip-licenses.exe"):
        full_path = os.path.join(venv_bin, candidate)
        if os.path.isfile(full_path):
            return full_path

    raise FileNotFoundError(
        f"pip-licenses not found in {venv_bin!r}. Run: poetry install --with dev"
    )


def get_package_licenses() -> list[dict[str, str]]:
    """
    Run ``pip-licenses --format=json`` in a subprocess and return the parsed list.

    pip-licenses inspects importlib.metadata for every installed distribution
    and reports the license field from its METADATA file.

    Returns:
        List of dicts, each with at least keys "Name" and "License".

    Raises:
        subprocess.CalledProcessError: if pip-licenses exits with a non-zero code.
        json.JSONDecodeError: if the output cannot be parsed as JSON.

    Time complexity:  O(n) where n = number of installed packages.
    Space complexity: O(n) — full JSON payload held in memory.
    """
    pip_licenses = _pip_licenses_executable()

    result = subprocess.run(  # noqa: S603 — trusted internal tool, not user input
        [pip_licenses, "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def find_copyleft_violations(packages: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Filter *packages* to those whose license field starts with a copyleft prefix.

    Comparison is case-insensitive so "gpl-2.0", "GPL-3.0", and "GPLv2"
    are all matched.

    Args:
        packages: Output of :func:`get_package_licenses`.

    Returns:
        Subset of *packages* that have a copyleft license.

    Time complexity:  O(n * k) where k = len(COPYLEFT_PREFIXES) — constant factor.
    Space complexity: O(v) where v = number of violations (typically 0).
    """
    return [
        pkg
        for pkg in packages
        if any(pkg.get("License", "").upper().startswith(prefix) for prefix in COPYLEFT_PREFIXES)
    ]


def main() -> None:
    """
    Entry point.  Exits 0 on success, 1 if copyleft licenses are detected.
    """
    try:
        packages = get_package_licenses()
    except subprocess.CalledProcessError as exc:
        # pip-licenses itself failed — surface the error and abort.
        print(f"ERROR: pip-licenses exited with code {exc.returncode}:", file=sys.stderr)
        print(exc.stderr, file=sys.stderr)
        sys.exit(1)

    violations = find_copyleft_violations(packages)

    if violations:
        print("ERROR: Copyleft license(s) detected in runtime dependencies:")
        for pkg in violations:
            # Print each violating package on its own line for easy scanning.
            print(f"  • {pkg['Name']}  —  {pkg['License']}")
        print()
        print("Remove or replace the above dependencies before committing.")
        print("Permissible licenses: MIT, Apache-2.0, BSD-*, ISC, PSF, HPND, etc.")
        sys.exit(1)

    # Happy path — report how many packages were scanned so the developer
    # can confirm the check ran (not silently skipped).
    print(f"License check passed: {len(packages)} packages scanned, 0 copyleft licenses found.")


if __name__ == "__main__":
    main()
