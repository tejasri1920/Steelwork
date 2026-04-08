# tests/test_logging_config.py
#
# Tests for the application logging configuration and log-emission behaviour.
#
# Two test classes:
#   TestSetupLogging  — unit-tests for setup_logging() itself: handler types,
#                       levels, formatter format string, rotation parameters,
#                       idempotency, and log-file creation.
#   TestLogEmission   — integration tests that call API endpoints through the
#                       FastAPI TestClient and assert that the expected log
#                       records are emitted at the correct severity levels.
#
# Key pytest fixtures used:
#   tmp_path   — built-in; provides a fresh temporary directory per test (pathlib.Path).
#   client     — from conftest.py; a TestClient wired to an in-memory SQLite DB.
#   seeded_db  — from conftest.py; seeds LOT-A / B / C / D into the test DB.
#   caplog     — built-in; captures log records emitted during a test without
#                needing real handlers.  Works independently of setup_logging().
#
# Why caplog instead of file assertions?
#   caplog operates at the logger level — it intercepts records before they reach
#   any handler.  Tests therefore work whether or not setup_logging() has been
#   called, making them fast and side-effect-free (no app.log files written).
#
# AC coverage:
#   Logging is cross-cutting infrastructure, not tied to a single AC.
#   These tests verify that observability is in place for every major code path.

import logging
import pathlib
from logging.handlers import RotatingFileHandler

import pytest
from fastapi.testclient import TestClient

from app.logging_config import setup_logging
from app.main import app

# ── Helpers ───────────────────────────────────────────────────────────────────


def _clear_root_handlers() -> None:
    """
    Remove all handlers from the root logger and reset its level to NOTSET.

    This is necessary before testing setup_logging() because logging.basicConfig
    is a no-op when the root logger already has handlers (which pytest may have
    installed).  Clearing them gives setup_logging() a blank slate.

    Each handler is closed before removal to release any open file descriptors
    (important for RotatingFileHandler on Windows where open files cannot be
    deleted or renamed while a handle is held).

    Time complexity:  O(H) where H = number of existing handlers (always small).
    Space complexity: O(1).
    """
    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()  # Release file descriptor / stream — prevents leaks
        root.removeHandler(handler)
    root.setLevel(logging.NOTSET)  # Reset level so setup_logging can set it freely


# ── Test class: setup_logging() unit tests ────────────────────────────────────


class TestSetupLogging:
    """
    Unit tests for app.logging_config.setup_logging().

    Each test clears the root logger's handler list first so that basicConfig
    is not a no-op, then calls setup_logging() with a tmp_path log file to
    avoid writing to the project directory.
    """

    def test_root_logger_level_is_debug(self, tmp_path: pathlib.Path) -> None:
        """
        setup_logging() sets the root logger's gate level to DEBUG.

        The root-level gate must be DEBUG so that DEBUG and INFO records are not
        silently discarded before they can reach the file handler.

        Time complexity:  O(1)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        assert logging.getLogger().level == logging.DEBUG

    def test_adds_exactly_two_handlers(self, tmp_path: pathlib.Path) -> None:
        """
        setup_logging() attaches exactly two handlers to the root logger:
        one StreamHandler (console) and one RotatingFileHandler (file).

        Time complexity:  O(1)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        assert len(logging.getLogger().handlers) == 2

    def test_console_handler_is_stream_handler_at_warning(self, tmp_path: pathlib.Path) -> None:
        """
        The console handler is a plain StreamHandler with level=WARNING.

        WARNING keeps the terminal output focused on actionable alerts; DEBUG
        and INFO noise is routed to the file instead.

        Time complexity:  O(H) — iterates over the (small, fixed) handler list.
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        root = logging.getLogger()
        # RotatingFileHandler is a subclass of StreamHandler, so we must use
        # `type(h) is logging.StreamHandler` (exact match) to exclude it.
        stream_handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
        assert len(stream_handlers) == 1, "Expected exactly one plain StreamHandler"
        assert stream_handlers[0].level == logging.WARNING

    def test_file_handler_is_rotating_at_debug(self, tmp_path: pathlib.Path) -> None:
        """
        The file handler is a RotatingFileHandler with level=DEBUG.

        DEBUG ensures every record (including development-level messages) is
        written to the log file for post-hoc diagnostics.

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1, "Expected exactly one RotatingFileHandler"
        assert file_handlers[0].level == logging.DEBUG

    def test_file_handler_max_bytes_is_5mb(self, tmp_path: pathlib.Path) -> None:
        """
        The RotatingFileHandler rotates when the log file reaches 5 MB (5_242_880 bytes).

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        fh = next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler))
        assert fh.maxBytes == 5 * 1024 * 1024

    def test_file_handler_backup_count_is_3(self, tmp_path: pathlib.Path) -> None:
        """
        The RotatingFileHandler keeps 3 backup files (app.log.1 – app.log.3).

        A 4th rotation would delete app.log.3, so at most 4 files exist at once:
        the active file plus 3 backups.

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        fh = next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler))
        assert fh.backupCount == 3

    def test_formatter_contains_levelname(self, tmp_path: pathlib.Path) -> None:
        """
        The log formatter includes %(levelname)s so severity is visible in every line.

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        fh = next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler))
        assert fh.formatter is not None
        assert "%(levelname)s" in fh.formatter._fmt  # type: ignore[union-attr]

    def test_formatter_contains_filename_and_lineno(self, tmp_path: pathlib.Path) -> None:
        """
        The formatter includes %(filename)s and %(lineno)d for source location.

        These fields make it trivial to find the exact line that emitted a log
        record without searching the codebase.

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        fh = next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler))
        assert fh.formatter is not None
        fmt = fh.formatter._fmt  # type: ignore[union-attr]
        assert "%(filename)s" in fmt
        assert "%(lineno)d" in fmt

    def test_formatter_contains_asctime(self, tmp_path: pathlib.Path) -> None:
        """
        The formatter includes %(asctime)s so every log line is timestamped.

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        fh = next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler))
        assert fh.formatter is not None
        assert "%(asctime)s" in fh.formatter._fmt  # type: ignore[union-attr]

    def test_formatter_contains_message(self, tmp_path: pathlib.Path) -> None:
        """
        The formatter includes %(message)s — the actual log text.

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        fh = next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler))
        assert fh.formatter is not None
        assert "%(message)s" in fh.formatter._fmt  # type: ignore[union-attr]

    def test_idempotent_does_not_duplicate_handlers(self, tmp_path: pathlib.Path) -> None:
        """
        Calling setup_logging() twice does not add a second set of handlers.

        basicConfig is a no-op when root already has handlers; the early-return
        guard in setup_logging() makes this behaviour explicit.

        Time complexity:  O(H)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        setup_logging(log_file=str(tmp_path / "test.log"))
        setup_logging(log_file=str(tmp_path / "test.log"))  # second call — must be a no-op
        assert len(logging.getLogger().handlers) == 2

    def test_log_file_created_after_write(self, tmp_path: pathlib.Path) -> None:
        """
        The RotatingFileHandler creates the log file on handler construction
        (delay=False default) or at latest on first write.

        Time complexity:  O(1)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        log_file = tmp_path / "test.log"
        setup_logging(log_file=str(log_file))
        # Emit a record to ensure the handler has flushed to disk.
        logging.getLogger("test_create").debug("hello from test")
        assert log_file.exists(), f"Expected log file at {log_file}"

    def test_custom_log_file_path_is_respected(self, tmp_path: pathlib.Path) -> None:
        """
        setup_logging(log_file=...) writes to the specified path, not 'app.log'.

        Time complexity:  O(1)
        Space complexity: O(1)
        """
        _clear_root_handlers()
        custom_path = tmp_path / "custom_app.log"
        setup_logging(log_file=str(custom_path))
        logging.getLogger("test_path").debug("path test")
        assert custom_path.exists()


# ── Test class: log-emission integration tests ────────────────────────────────


class TestLogEmission:
    """
    Integration tests that verify log records are emitted when API endpoints
    are called.  Uses pytest's caplog fixture, which captures records at the
    logger level independently of handler configuration.

    All tests use the `seeded_client` fixture so the DB contains LOT-A / B / C / D.

    Fixture dependency chain:
        seeded_client → seeded_db → db → (app dependency override registered)
    """

    @pytest.fixture
    def seeded_client(self, seeded_db):  # type: ignore[no-untyped-def]
        """
        A FastAPI TestClient backed by the seeded in-memory DB.

        seeded_db (from conftest.py) registers the test session as the app's
        get_db override, so all requests use the seeded SQLite database.

        Time complexity:  O(1)
        Space complexity: O(1)
        """
        return TestClient(app)

    # ── /lots endpoints ───────────────────────────────────────────────────────

    def test_list_lots_emits_info(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/lots/ emits an INFO record from app.routers.lots.

        Time complexity:  O(N) — request touches all lots in the test DB.
        Space complexity: O(1)
        """
        with caplog.at_level(logging.INFO):
            response = seeded_client.get("/api/v1/lots/")
        assert response.status_code == 200
        info_records = [
            r for r in caplog.records if r.name == "app.routers.lots" and r.levelno == logging.INFO
        ]
        assert len(info_records) >= 1, "Expected at least one INFO record from app.routers.lots"

    def test_get_existing_lot_emits_info_with_lot_code(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/lots/LOT-A emits an INFO record containing the lot_code.

        Having the lot_code in the log message lets operators correlate a log
        line with the specific lot that was requested.

        Time complexity:  O(P+I+S) — request fetches all child records for LOT-A.
        Space complexity: O(1)
        """
        with caplog.at_level(logging.INFO):
            response = seeded_client.get("/api/v1/lots/LOT-A")
        assert response.status_code == 200
        info_records = [
            r for r in caplog.records if r.name == "app.routers.lots" and r.levelno == logging.INFO
        ]
        assert len(info_records) >= 1
        assert any("LOT-A" in r.message for r in info_records), (
            "INFO message should contain the requested lot_code"
        )

    def test_get_missing_lot_emits_warning(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/lots/NONEXISTENT emits a WARNING from app.routers.lots.

        A missing lot is a client error (bad lot_code), not a server fault.
        WARNING is the correct level so operators can distinguish bad requests
        from bugs without the noise of ERROR-level alerting.

        Time complexity:  O(1) — lot lookup returns immediately on miss.
        Space complexity: O(1)
        """
        with caplog.at_level(logging.WARNING):
            response = seeded_client.get("/api/v1/lots/NONEXISTENT")
        assert response.status_code == 404
        warning_records = [
            r
            for r in caplog.records
            if r.name == "app.routers.lots" and r.levelno == logging.WARNING
        ]
        assert len(warning_records) >= 1, "Expected at least one WARNING for 404 response"
        assert any("NONEXISTENT" in r.message for r in warning_records), (
            "WARNING message should include the unknown lot_code"
        )

    def test_list_lots_emits_debug_with_result_count(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/lots/ emits a DEBUG record containing the result count.

        Repository-level DEBUG records help diagnose why fewer lots than expected
        are returned without needing to add ad-hoc print statements.

        Time complexity:  O(N)
        Space complexity: O(1)
        """
        with caplog.at_level(logging.DEBUG):
            response = seeded_client.get("/api/v1/lots/")
        assert response.status_code == 200
        debug_records = [
            r for r in caplog.records if r.name == "app.routers.lots" and r.levelno == logging.DEBUG
        ]
        assert len(debug_records) >= 1, "Expected DEBUG record from app.routers.lots"

    # ── /reports endpoints ────────────────────────────────────────────────────

    def test_lot_summary_emits_info(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/reports/lot-summary emits an INFO record naming the endpoint.

        Time complexity:  O(N)
        Space complexity: O(1)
        """
        with caplog.at_level(logging.INFO):
            response = seeded_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        info_records = [
            r
            for r in caplog.records
            if r.name == "app.routers.reports" and r.levelno == logging.INFO
        ]
        assert len(info_records) >= 1
        assert any("lot-summary" in r.message for r in info_records)

    def test_inspection_issues_emits_info(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/reports/inspection-issues emits an INFO record.

        Time complexity:  O(F) where F = flagged inspection records.
        Space complexity: O(1)
        """
        with caplog.at_level(logging.INFO):
            response = seeded_client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        info_records = [
            r
            for r in caplog.records
            if r.name == "app.routers.reports" and r.levelno == logging.INFO
        ]
        assert len(info_records) >= 1
        assert any("inspection-issues" in r.message for r in info_records)

    def test_incomplete_lots_emits_info(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/reports/incomplete-lots emits an INFO record.

        Time complexity:  O(I) where I = incomplete lots.
        Space complexity: O(1)
        """
        with caplog.at_level(logging.INFO):
            response = seeded_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        info_records = [
            r
            for r in caplog.records
            if r.name == "app.routers.reports" and r.levelno == logging.INFO
        ]
        assert len(info_records) >= 1
        assert any("incomplete-lots" in r.message for r in info_records)

    def test_line_issues_emits_info(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /api/v1/reports/line-issues emits an INFO record.

        Time complexity:  O(P+I) where P, I = production and inspection record counts.
        Space complexity: O(1)
        """
        with caplog.at_level(logging.INFO):
            response = seeded_client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        info_records = [
            r
            for r in caplog.records
            if r.name == "app.routers.reports" and r.levelno == logging.INFO
        ]
        assert len(info_records) >= 1
        assert any("line-issues" in r.message for r in info_records)

    def test_report_repo_emits_debug(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        The report repository emits DEBUG records that include row counts.

        Repository-level DEBUG records are important for diagnosing query
        performance issues without needing SQL profiling tools.

        Time complexity:  O(N)
        Space complexity: O(1)
        """
        with caplog.at_level(logging.DEBUG):
            response = seeded_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        repo_debug = [
            r
            for r in caplog.records
            if r.name == "app.repositories.report_repo" and r.levelno == logging.DEBUG
        ]
        assert len(repo_debug) >= 1, (
            "Expected at least one DEBUG record from app.repositories.report_repo"
        )

    def test_lot_repo_emits_debug(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        The lot repository emits DEBUG records with query result counts.

        Time complexity:  O(N)
        Space complexity: O(1)
        """
        with caplog.at_level(logging.DEBUG):
            response = seeded_client.get("/api/v1/lots/")
        assert response.status_code == 200
        repo_debug = [
            r
            for r in caplog.records
            if r.name == "app.repositories.lot_repo" and r.levelno == logging.DEBUG
        ]
        assert len(repo_debug) >= 1, (
            "Expected at least one DEBUG record from app.repositories.lot_repo"
        )

    def test_health_check_emits_debug(
        self, seeded_client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        GET /health emits a DEBUG record from app.main.

        Time complexity:  O(1)
        Space complexity: O(1)
        """
        with caplog.at_level(logging.DEBUG):
            response = seeded_client.get("/health")
        assert response.status_code == 200
        debug_records = [
            r for r in caplog.records if r.name == "app.main" and r.levelno == logging.DEBUG
        ]
        assert len(debug_records) >= 1, "Expected DEBUG record from app.main for /health"
