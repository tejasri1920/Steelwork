# tests/test_reports.py
#
# Unit tests for the four report API endpoints.
#
# Endpoints under test:
#   GET /api/v1/reports/lot-summary          → lot_summary()
#   GET /api/v1/reports/inspection-issues    → inspection_issues()
#   GET /api/v1/reports/incomplete-lots      → incomplete_lots()
#   GET /api/v1/reports/line-issues          → line_issues()
#
# AC coverage:
#   AC1  — cross-function view (lot-summary)
#   AC4  — incomplete lots (incomplete-lots endpoint)
#   AC5  — line issues (line-issues endpoint)
#   AC6  — flagged lots with shipment status (inspection-issues endpoint)
#   AC7  — meeting summary (lot-summary endpoint)
#   AC8  — shipment status (lot-summary endpoint)
#   AC10 — completeness scores (lot-summary, incomplete-lots endpoints)
#
# Helper:
#   _lot_id_map(client) — fetches GET /api/v1/lots/ and returns {lot_code: lot_id}.
#   Used to resolve auto-assigned lot_ids without hardcoding them.

from fastapi.testclient import TestClient


def _lot_id_map(client: TestClient) -> dict[str, int]:
    """
    Return a mapping of lot_code → lot_id by calling the lots list endpoint.

    The lot_id is an auto-incrementing integer assigned by SQLite. We cannot
    predict its value ahead of time, so report tests that filter by lot_id must
    look it up dynamically.

    Time complexity:  O(N) — one HTTP call + one dict build, N = number of lots.
    Space complexity: O(N).
    """
    response = client.get("/api/v1/lots/")
    assert response.status_code == 200
    return {row["lot_code"]: row["lot_id"] for row in response.json()}


# ── GET /api/v1/reports/lot-summary ──────────────────────────────────────────


class TestLotSummary:
    """Tests for GET /api/v1/reports/lot-summary."""

    def test_lot_summary_returns_200_with_empty_list(self, client: TestClient) -> None:
        """
        When the database is empty, the endpoint returns HTTP 200 with [].

        AC7: Baseline — endpoint is reachable.
        """
        response = client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        assert response.json() == []

    def test_lot_summary_returns_one_row_per_lot(self, client: TestClient, seeded_db) -> None:
        """
        With four seeded lots, the summary returns exactly four rows.

        AC7: One aggregated row per lot.
        """
        response = client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        assert len(response.json()) == 4

    def test_lot_summary_lot_a_has_correct_aggregates(self, client: TestClient, seeded_db) -> None:
        """
        LOT-A: total_produced=500, any_issues=False, latest_status='Delivered',
               overall_completeness=100.

        AC1:  All domains visible in one row.
        AC7:  Aggregates are correct.
        AC8:  latest_status reflects actual shipment state.
        AC10: Completeness score is 100.
        """
        lot_ids = _lot_id_map(client)
        response = client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["lot_id"] == lot_ids["LOT-A"])
        assert row["total_produced"] == 500
        assert row["any_issues"] is False
        assert row["latest_status"] == "Delivered"
        assert float(row["overall_completeness"]) == 100

    def test_lot_summary_lot_d_has_null_aggregates(self, client: TestClient, seeded_db) -> None:
        """
        LOT-D has no child records — all aggregate columns should be None/null.
        overall_completeness should be 0.

        AC10: Lot with no data has completeness = 0.
        """
        lot_ids = _lot_id_map(client)
        response = client.get("/api/v1/reports/lot-summary")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["lot_id"] == lot_ids["LOT-D"])
        assert row["total_produced"] is None
        assert row["any_issues"] is None
        assert row["latest_status"] is None
        assert float(row["overall_completeness"]) == 0


# ── GET /api/v1/reports/inspection-issues ────────────────────────────────────


class TestInspectionIssues:
    """Tests for GET /api/v1/reports/inspection-issues."""

    def test_inspection_issues_returns_200_with_empty_list(self, client: TestClient) -> None:
        """
        When no flagged inspections exist, returns HTTP 200 with [].
        """
        response = client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        assert response.json() == []

    def test_inspection_issues_returns_only_flagged_lots(
        self, client: TestClient, seeded_db
    ) -> None:
        """
        Only LOT-C has issue_flag=True. LOT-A (Pass, no flag) must not appear.

        AC5: Only flagged lots are included.
        """
        lot_ids = _lot_id_map(client)
        response = client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["lot_id"] == lot_ids["LOT-C"]

    def test_inspection_issues_lot_c_has_on_hold_status(
        self, client: TestClient, seeded_db
    ) -> None:
        """
        LOT-C has issue_flag=True and shipment_status='On Hold'.

        AC6: Flagged lots show their current shipment status.
        """
        response = client.get("/api/v1/reports/inspection-issues")
        assert response.status_code == 200
        row = response.json()[0]
        assert row["issue_flag"] is True
        assert row["shipment_status"] == "On Hold"


# ── GET /api/v1/reports/incomplete-lots ──────────────────────────────────────


class TestIncompleteLots:
    """Tests for GET /api/v1/reports/incomplete-lots."""

    def test_incomplete_lots_returns_200_with_empty_list(self, client: TestClient) -> None:
        """
        When no lots exist (empty DB), returns HTTP 200 with [].
        """
        response = client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        assert response.json() == []

    def test_incomplete_lots_excludes_fully_complete_lots(
        self, client: TestClient, seeded_db
    ) -> None:
        """
        LOT-A (100%) and LOT-C (100%) must NOT appear.
        LOT-B (67%) and LOT-D (0%) MUST appear.

        AC4:  Only incomplete lots are surfaced.
        AC10: overall_completeness < 100 is the filter criterion.
        """
        lot_ids = _lot_id_map(client)
        response = client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        returned_ids = {r["lot_id"] for r in data}
        assert returned_ids == {lot_ids["LOT-B"], lot_ids["LOT-D"]}

    def test_incomplete_lots_ordered_by_completeness_ascending(
        self, client: TestClient, seeded_db
    ) -> None:
        """
        Results are ordered most-incomplete first: LOT-D (0%) before LOT-B (67%).

        AC4: Most urgent gaps are at the top.
        """
        response = client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        rows = response.json()
        assert float(rows[0]["overall_completeness"]) == 0  # LOT-D
        assert float(rows[1]["overall_completeness"]) == 67  # LOT-B

    def test_incomplete_lots_flags_are_correct_for_lot_b(
        self, client: TestClient, seeded_db
    ) -> None:
        """
        LOT-B: has_production_data=True, has_inspection_data=False, has_shipping_data=True.

        AC4: Individual domain flags show exactly which data is missing.
        """
        lot_ids = _lot_id_map(client)
        response = client.get("/api/v1/reports/incomplete-lots")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["lot_id"] == lot_ids["LOT-B"])
        assert row["has_production_data"] is True
        assert row["has_inspection_data"] is False
        assert row["has_shipping_data"] is True


# ── GET /api/v1/reports/line-issues ──────────────────────────────────────────


class TestLineIssues:
    """Tests for GET /api/v1/reports/line-issues."""

    def test_line_issues_returns_200_with_empty_list(self, client: TestClient) -> None:
        """
        When no production or inspection records exist, returns HTTP 200 with [].
        """
        response = client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        assert response.json() == []

    def test_line_issues_row_has_required_fields(self, client: TestClient, seeded_db) -> None:
        """
        Each row must contain production_line, total_inspections, total_issues,
        issue_rate_pct.

        AC5: All fields needed to evaluate line performance are present.
        """
        response = client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) > 0
        row = rows[0]
        assert "production_line" in row
        assert "total_inspections" in row
        assert "total_issues" in row
        assert "issue_rate_pct" in row

    def test_line_issues_line_3_has_highest_issue_count(
        self, client: TestClient, seeded_db
    ) -> None:
        """
        LOT-C ran on Line 3 and has issue_flag=True.
        Line 3 should appear first (ordered by total_issues DESC).

        AC5: Line with the most issues is ranked first.
        """
        response = client.get("/api/v1/reports/line-issues")
        assert response.status_code == 200
        rows = response.json()
        assert rows[0]["production_line"] == "Line 3"
        assert rows[0]["total_issues"] == 1
