# tests/integration/test_reports_pg.py
#
# Integration tests for the /api/v1/reports/* endpoints against real PostgreSQL.
#
# These tests verify that all four report queries work correctly with the ops
# schema, real JOIN logic, and trigger-populated data_completeness rows.
#
# Report schema field reference:
#   LotSummaryRow      lot_id, start_date, end_date, total_produced, lines_used,
#                      any_issues, issue_count, latest_status, overall_completeness
#   InspectionIssueRow lot_id, inspection_result, issue_flag,
#                      shipment_status, ship_date, destination
#   IncompleteLotRow   lot_id, start_date, end_date,
#                      has_production_data, has_inspection_data, has_shipping_data,
#                      overall_completeness
#   LineIssueRow       production_line, total_inspections, total_issues, issue_rate_pct
#
# Lot IDs are not known until the pg_seed_db fixture runs.  Tests that need to
# identify specific seeded rows accept `pg_seed_db` as a parameter to get the
# dict{"INT-A": lot_id_a, "INT-B": lot_id_b, ...} that the fixture yields.
#
# Test matrix:
#   TestIntLotSummary       — GET /api/v1/reports/lot-summary      (AC1, AC7, AC8, AC10)
#   TestIntInspectionIssues — GET /api/v1/reports/inspection-issues (AC5, AC6)
#   TestIntIncompleteLots   — GET /api/v1/reports/incomplete-lots   (AC4, AC10)
#   TestIntLineIssues       — GET /api/v1/reports/line-issues       (AC5)
#
# All tests require TEST_DATABASE_URL in .env.test.
# They are skipped automatically when that variable is absent.

import pytest
from fastapi.testclient import TestClient


class TestIntLotSummary:
    """
    Integration tests for GET /api/v1/reports/lot-summary

    Verifies the aggregated cross-domain view includes the seeded lots.
    """

    def test_returns_all_seeded_lots(self, pg_client: TestClient, pg_seed_db: dict) -> None:
        """
        The lot-summary report must include a row for each of INT-A through INT-D.

        AC1:  Cross-function view — all seeded lots appear.
        AC7:  One row per lot — suitable for operations meetings.
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        response_lot_ids = {r["lot_id"] for r in response.json()}
        # All four seeded lot_ids must appear in the report
        assert set(pg_seed_db.values()).issubset(response_lot_ids)

    def test_lot_a_row_has_correct_totals(self, pg_client: TestClient, pg_seed_db: dict) -> None:
        """
        The INT-A summary row must reflect 500 units produced, no issues,
        Delivered shipment, and 100% completeness.

        AC8:  Shipment status visible in summary.
        AC10: Completeness score present in every row.
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        lot_a_id = pg_seed_db["INT-A"]
        row = next(r for r in response.json() if r["lot_id"] == lot_a_id)

        assert row["total_produced"] == 500
        assert row["latest_status"] == "Delivered"
        assert float(row["overall_completeness"]) == 100.0

    def test_lot_b_missing_inspection_in_summary(
        self, pg_client: TestClient, pg_seed_db: dict
    ) -> None:
        """
        INT-B has no inspection record — any_issues and issue_count must be null.

        AC1: Cross-domain view handles missing domains gracefully (null, not error).
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        lot_b_id = pg_seed_db["INT-B"]
        row = next(r for r in response.json() if r["lot_id"] == lot_b_id)

        assert row["any_issues"] is None
        assert row["issue_count"] is None

    def test_lot_c_flagged_in_summary(self, pg_client: TestClient, pg_seed_db: dict) -> None:
        """
        INT-C has a Fail inspection (any_issues=True) and an On Hold shipment.

        AC6: Flagged lots and their shipment status visible in one place.
        AC8: Latest shipment status included.
        """
        response = pg_client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        lot_c_id = pg_seed_db["INT-C"]
        row = next(r for r in response.json() if r["lot_id"] == lot_c_id)

        assert row["any_issues"] is True
        assert row["latest_status"] == "On Hold"


class TestIntInspectionIssues:
    """
    Integration tests for GET /api/v1/reports/inspection-issues

    Only lots with issue_flag=True should appear.
    """

    def test_only_flagged_lots_returned(self, pg_client: TestClient, pg_seed_db: dict) -> None:
        """
        The inspection-issues report must include INT-C (issue_flag=True) and must
        NOT include INT-A (issue_flag=False) or INT-B (no inspection).

        AC5: Identify lots with quality problems.
        AC6: Track flagged lots to their shipment outcome.
        """
        response = pg_client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        rows = response.json()
        response_lot_ids = {r["lot_id"] for r in rows}
        assert pg_seed_db["INT-C"] in response_lot_ids
        assert pg_seed_db["INT-A"] not in response_lot_ids
        assert pg_seed_db["INT-B"] not in response_lot_ids

    def test_lot_c_issue_details(self, pg_client: TestClient, pg_seed_db: dict) -> None:
        """
        INT-C's row must have issue_flag=True, Fail result, and On Hold status.

        AC5: Flagged inspection is surfaced for root-cause analysis.
        AC6: On Hold shipment status confirms the lot was withheld.
        """
        response = pg_client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        lot_c_id = pg_seed_db["INT-C"]
        row = next(r for r in response.json() if r["lot_id"] == lot_c_id)

        assert row["issue_flag"] is True
        assert row["inspection_result"] == "Fail"
        assert row["shipment_status"] == "On Hold"


class TestIntIncompleteLots:
    """
    Integration tests for GET /api/v1/reports/incomplete-lots

    Only lots with overall_completeness < 100 should appear, ordered ascending.
    """

    def test_incomplete_lots_excludes_complete_lots(
        self, pg_client: TestClient, pg_seed_db: dict
    ) -> None:
        """
        INT-A (100%) and INT-C (100%) must NOT appear.
        INT-B (67%) and INT-D (0%) must appear.

        AC4:  Surface lots with missing data before meetings.
        AC10: Only genuinely incomplete lots are listed.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        response_lot_ids = {r["lot_id"] for r in response.json()}
        assert pg_seed_db["INT-B"] in response_lot_ids
        assert pg_seed_db["INT-D"] in response_lot_ids
        assert pg_seed_db["INT-A"] not in response_lot_ids
        assert pg_seed_db["INT-C"] not in response_lot_ids

    def test_incomplete_lots_ordered_ascending(
        self, pg_client: TestClient, pg_seed_db: dict
    ) -> None:
        """
        INT-D (0%) must appear before INT-B (67%) — ascending completeness order.

        AC4: Most incomplete lots surface at the top of the report.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = response.json()
        int_rows = [r for r in rows if r["lot_id"] in (pg_seed_db["INT-B"], pg_seed_db["INT-D"])]
        assert len(int_rows) == 2
        ids_in_order = [r["lot_id"] for r in int_rows]
        assert ids_in_order.index(pg_seed_db["INT-D"]) < ids_in_order.index(pg_seed_db["INT-B"])

    def test_completeness_scores_are_correct(self, pg_client: TestClient, pg_seed_db: dict) -> None:
        """
        INT-B: ~67%, INT-D: 0% — values driven by real PostgreSQL triggers.

        AC10: Trigger-driven completeness scores are accurate.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = {r["lot_id"]: r for r in response.json()}

        assert float(rows[pg_seed_db["INT-B"]]["overall_completeness"]) == pytest.approx(67, abs=1)
        assert float(rows[pg_seed_db["INT-D"]]["overall_completeness"]) == pytest.approx(0, abs=1)

    def test_missing_data_flags(self, pg_client: TestClient, pg_seed_db: dict) -> None:
        """
        has_* flags must accurately reflect which domains are absent.

        INT-B: has_inspection_data=False; production and shipping present.
        INT-D: all three domain flags are False.

        AC4: Analyst can see at a glance which domain is missing.
        """
        response = pg_client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = {r["lot_id"]: r for r in response.json()}

        int_b = rows[pg_seed_db["INT-B"]]
        assert int_b["has_inspection_data"] is False
        assert int_b["has_production_data"] is True
        assert int_b["has_shipping_data"] is True

        int_d = rows[pg_seed_db["INT-D"]]
        assert int_d["has_production_data"] is False
        assert int_d["has_inspection_data"] is False
        assert int_d["has_shipping_data"] is False


class TestIntLineIssues:
    """
    Integration tests for GET /api/v1/reports/line-issues

    Verifies per-production-line issue aggregation.
    """

    def test_line_3_has_issues(self, pg_client: TestClient) -> None:
        """
        INT-C is produced on Line 3 with a flagged inspection.
        Line 3 must appear with at least 1 issue.

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
        INT-A is produced on Line 2 with a Pass inspection (issue_flag=False).
        If Line 2 appears, its issue count must be 0.

        AC5: Lines with no issues should be visible with a 0% rate.
        """
        response = pg_client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        rows = response.json()
        line2 = next((r for r in rows if r["production_line"] == "Line 2"), None)
        if line2 is not None:
            assert line2["total_issues"] == 0
            assert float(line2["issue_rate_pct"]) == 0.0

    def test_ordered_by_issues_descending(self, pg_client: TestClient) -> None:
        """
        Rows must be ordered by total_issues descending so the worst lines appear first.

        AC5: Highest-risk lines surface at the top.
        """
        response = pg_client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        rows = response.json()
        totals = [r["total_issues"] for r in rows]
        assert totals == sorted(totals, reverse=True), (
            "line-issues must be ordered by total_issues descending"
        )
