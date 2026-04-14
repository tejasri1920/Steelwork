# app/logging_config.py
#
# Centralised logging configuration for the Steelworks Ops Analytics backend.
#
# Design:
#   Two handlers are attached to the root logger:
#     1. StreamHandler  — sends WARNING+ to the terminal (visible in Docker logs).
#     2. RotatingFileHandler — writes DEBUG+ to app.log; rotates at 5 MB, keeps 3 backups.
#
#   Root logger gate is set to DEBUG so all records reach both handlers; each
#   handler then applies its own level filter.  This is intentional: raising the
#   root level to WARNING would silently kill DEBUG and INFO records before they
#   could ever reach the file handler — even if the file handler's own level is DEBUG.
#
# Usage:
#   from app.logging_config import setup_logging
#   setup_logging()                          # production: writes to "app.log"
#   setup_logging(log_file="/tmp/test.log")  # tests / alternate paths
#
# Idempotency:
#   setup_logging() checks whether the root logger already has handlers before
#   configuring.  This prevents duplicate handlers if the function is called
#   more than once (e.g. on uvicorn auto-reload).

import logging
import tempfile
from logging.handlers import RotatingFileHandler

# Format used by both handlers.
# Columns (separated by " | "):
#   %(asctime)s    — timestamp: when the event occurred, e.g. "2026-04-08 14:05:03"
#   %(levelname)s  — severity level: DEBUG / INFO / WARNING / ERROR / CRITICAL
#   %(filename)s:%(lineno)d — source file and line number where the log call was made
#   %(message)s    — the message passed to logger.info(...) etc.
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # Drop milliseconds for readability


def setup_logging(log_file: str = "") -> None:
    """
    Configure application-wide logging with a console and a rotating file handler.

    This function is idempotent: if the root logger already has handlers (e.g. because
    uvicorn reloaded or a test already called this function), it returns immediately
    without adding duplicates.

    Args:
        log_file: Path for the rotating log file.  Defaults to "app.log" inside
                  the platform temp directory (tempfile.gettempdir()), which is
                  writable on Linux containers, macOS, and Windows alike.

    Handler summary:
        console_handler  — StreamHandler,        level=WARNING,  output=stderr
        file_handler     — RotatingFileHandler,  level=DEBUG,    output=log_file
                           maxBytes=5 MB, backupCount=3

    Backup file naming (RotatingFileHandler convention):
        app.log    ← current file, always being written to
        app.log.1  ← previous file (most recent rotation)
        app.log.2  ← one before that
        app.log.3  ← oldest kept; a hypothetical .4 would be deleted

    Time complexity:  O(1) — fixed number of handlers regardless of runtime state.
    Space complexity: O(1) — no collections created at runtime.
    """
    # Resolve the default log path using the platform temp dir.
    # tempfile.gettempdir() returns:
    #   /tmp         on Linux (Docker containers)
    #   /var/folders/ on macOS
    #   C:\Users\...\AppData\Local\Temp  on Windows
    # This avoids PermissionError when the process runs as a non-root user in Docker.
    if not log_file:
        import os

        log_file = os.path.join(tempfile.gettempdir(), "app.log")

    root = logging.getLogger()

    # Idempotency guard: basicConfig is a no-op when handlers already exist, but
    # this explicit check makes the intent clear and avoids building handler objects
    # unnecessarily on repeated calls.
    if root.handlers:
        return

    # ── Handlers ──────────────────────────────────────────────────────────────

    # Console handler: WARNING and above only — keeps terminal output focused on
    # actionable alerts without the noise of DEBUG / INFO development messages.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # File handler: everything (DEBUG+), rotates when the file hits 5 MB.
    # encoding="utf-8" ensures non-ASCII characters (e.g. part numbers with
    # accented letters) are stored safely.
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file — rotate when file hits this size
        backupCount=3,  # keep up to 3 rotated backups before discarding
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # ── Formatter ─────────────────────────────────────────────────────────────

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # ── Root logger ───────────────────────────────────────────────────────────
    # level=DEBUG is the GATE, not a duplicate of the handler levels.
    # A log record must pass this root-level check before reaching any handler.
    # If this were WARNING, DEBUG and INFO records would be discarded here and the
    # file handler would never see them — regardless of its own level=DEBUG setting.
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[console_handler, file_handler],
    )
