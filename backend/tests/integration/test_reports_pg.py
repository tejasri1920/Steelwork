# tests/integration/test_reports_pg.py
#
# Integration tests for the /api/v1/reports/* endpoints against real PostgreSQL.
#
# These tests verify that all four report queries work correctly with the ops
# schema, real JOIN logic, and trigger-populated data_completeness rows.
#
# Test matrix:
#   TestIntLotSummary       — GET /api/v1/reports/lot-summary      (AC1, AC7, AC8, AC10)
#   TestIntInspectionIssues — GET /api/v1/reports/inspection-issues (AC5, AC6)
#   TestIntIncompleteLots   — GET /api/v1/reports/incomplete-lots   (AC4, AC10)
#   TestIntLineIssues       — GET /api/v1/reports/line-issues       (AC5)
#
# All tests depend on the pg_seed_db session-scoped fixture from
# tests/integration/conftest.py.  If TEST_DATABASE_URL is not set, the module
# is skipped automatically.

import pytest
from fastapi.testclient import TestClient


class TestIntLotSummary:
    """
    Integration tests for GET /api/v1/reports/lot-summary

    Verifies the aggregated cross-domain view includes the seeded lots.
    """

    def test_returns_all_seeded_lots(self, pg_client: TestClient) -> None:
        """
        The lot-summary report must include a row for each of INT-A through INT-D.

        AC1:  Cross-function view — production totals, inspection flags, and
              shipment status appear together.
        AC7:  One row per lot — suitable for operations meetings.
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        rows = response.json()
        codes = {r["lot_code"] for r in rows}
        assert {"INT-A", "INT-B", "INT-C", "INT-D"}.issubset(codes)

    def test_lot_a_row_has_correct_totals(self, pg_client: TestClient) -> None:
        """
        The INT-A summary row must reflect 500 units produced, Pass inspection,
        Delivered shipment, and 100% completeness.

        AC8:  Shipment status visible in summary.
        AC10: Completeness score present in every row.
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["lot_code"] == "INT-A")

        assert row["total_quantity_produced"] == 500
        assert row["inspection_result"] == "Pass"
        assert row["latest_status"] == "Delivered"
        assert float(row["overall_completeness"]) == 100.0

    def test_lot_b_missing_inspection_in_summary(self, pg_client: TestClient) -> None:
        """
        INT-B has no inspection record — inspection_result and issue_flag must be null.

        AC1: Cross-domain view handles missing domains gracefully (null, not error).
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["lot_code"] == "INT-B")

        assert row["inspection_result"] is None
        assert row["issue_flag"] is None

    def test_lot_c_flagged_in_summary(self, pg_client: TestClient) -> None:
        """
        INT-C has a Fail inspection with issue_flag=True — both must appear in the
        summary row alongside the On Hold shipment status.

        AC6: Flagged lots and their shipment status visible in one place.
        AC8: Latest shipment status included.
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["lot_code"] == "INT-C")

        assert row["issue_flag"] is True
        assert row["latest_status"] == "On Hold"


class TestIntInspectionIssues:
    """
    Integration tests for GET /api/v1/reports/inspection-issues

    Only lots with issue_flag=True should appear.
    """

    def test_only_flagged_lots_returned(self, pg_client: TestClient) -> None:
        """
        The inspection-issues report must include INT-C (issue_flag=True) and must
        NOT include INT-A (issue_flag=False) or INT-B (no inspection).

        AC5: Identify lots with quality problems.
        AC6: Track flagged lots to their shipment outcome.
        """
        response = pg_client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        rows = response.json()
        codes = {r["lot_code"] for r in rows}
        assert "INT-C" in codes
        assert "INT-A" not in codes
        assert "INT-B" not in codes

    def test_lot_c_issue_details(self, pg_client: TestClient) -> None:
        """
        INT-C's row must include the correct issue_category and the On Hold status.

        AC5: Issue category (Dimensional) is surfaced for root-cause analysis.
        AC6: On Hold shipment status confirms the lot was withheld.
        """
        response = pg_client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["lot_code"] == "INT-C")

        assert row["issue_category"] == "Dimensional"
        assert row["shipment_status"] == "On Hold"


class TestIntIncompleteLots:
    """
    Integration tests for GET /api/v1/reports/incomplete-lots

    Only lots with overall_completeness < 100 should appear, ordered ascending.
    """

    def test_incomplete_lots_excludes_complete_lots(self, pg_client: TestClient) -> None:
        """
        INT-A (100%) and INT-C (100%) must NOT appear.
        INT-B (67%) and INT-D (0%) must appear.

        AC4:  Surface lots with missing data before meetings.
        AC10: Only genuinely incomplete lots are listed.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = response.json()
        codes = {r["lot_code"] for r in rows}
        assert "INT-B" in codes
        assert "INT-D" in codes
        assert "INT-A" not in codes
        assert "INT-C" not in codes

    def test_incomplete_lots_ordered_ascending(self, pg_client: TestClient) -> None:
        """
        Rows must be ordered by overall_completeness ascending so the most
        incomplete lots appear first.

        INT-D (0%) should appear before INT-B (67%) among the seeded lots.

        AC4: Most incomplete lots surface at the top of the report.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = response.json()
        int_rows = [r for r in rows if r["lot_code"] in ("INT-B", "INT-D")]

        # INT-D must come before INT-B in the sorted result
        assert len(int_rows) == 2
        codes_in_order = [r["lot_code"] for r in int_rows]
        assert codes_in_order.index("INT-D") < codes_in_order.index("INT-B")

    def test_completeness_scores_are_correct(self, pg_client: TestClient) -> None:
        """
        Completeness scores must match trigger logic:
            INT-B: 2/3 domains → ~67%
            INT-D: 0/3 domains →   0%

        AC10: Trigger-driven completeness scores are accurate.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = {r["lot_code"]: r for r in response.json()}

        assert float(rows["INT-B"]["overall_completeness"]) == pytest.approx(67, abs=1)
        assert float(rows["INT-D"]["overall_completeness"]) == pytest.approx(0, abs=1)

    def test_missing_data_flags(self, pg_client: TestClient) -> None:
        """
        The missing-data flag columns must accurately reflect which domains are absent.

        INT-B: has_inspection_data=False; production and shipping present.
        INT-D: all three domain flags are False.

        AC4: Analyst can see at a glance which domain is missing.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = {r["lot_code"]: r for r in response.json()}

        assert rows["INT-B"]["has_inspection_data"] is False
        assert rows["INT-B"]["has_production_data"] is True
        assert rows["INT-B"]["has_shipping_data"] is True

        assert rows["INT-D"]["has_production_data"] is False
        assert rows["INT-D"]["has_inspection_data"] is False
        assert rows["INT-D"]["has_shipping_data"] is False


class TestIntLineIssues:
    """
    Integration tests for GET /api/v1/reports/line-issues

    Verifies per-production-line issue aggregation.
    """

    def test_line_3_has_issues(self, pg_client: TestClient) -> None:
        """
        INT-C is produced on Line 3 with a flagged inspection.
        Line 3 must appear in the line-issues report with at least 1 issue.

        AC5: Identify which production lines have quality problems.
        """
        response = pg_client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        rows = response.json()
        line3 = next((r for r in rows if r["production_line"] == "Line 3"), None)
        assert line3 is not None
        assert line3["total_issues"] >= 1
        assert float(line3["issue_rate_pct"]) > 0

    def test_line_2_has_no_issues(self, pg_client: TestClient) -> None:
        """
        INT-A is produced on Line 2 with a Pass inspection (no flag).
        Line 2 must appear with 0 issues (or not appear if filtered to issue_flag=True).

        AC5: Lines with no issues should be visible with a 0% rate.
        """
        response = pg_client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        rows = response.json()
        line2 = next((r for r in rows if r["production_line"] == "Line 2"), None)
        # Line 2 appears only if there is at least one inspection for that line.
        # If it appears, its issue count must be 0.
        if line2 is not None:
            assert line2["total_issues"] == 0
            assert float(line2["issue_rate_pct"]) == 0.0

    def test_ordered_by_issues_descending(self, pg_client: TestClient) -> None:
        """
        Lines with the most issues must appear first (descending by total_issues).

        If Line 3 (1 issue) and Line 2 (0 issues) both appear, Line 3 must come
        first in the ordering.

        AC5: Highest-risk lines surface at the top.
        """
        response = pg_client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        rows = response.json()
        # Verify non-increasing order of total_issues across all returned rows.
        totals = [r["total_issues"] for r in rows]
        assert totals == sorted(totals, reverse=True), (
            "line-issues must be ordered by total_issues descending"
        )
