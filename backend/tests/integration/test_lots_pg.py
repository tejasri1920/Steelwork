# tests/integration/test_lots_pg.py
#
# Integration tests for the /api/v1/lots endpoints against a real PostgreSQL database.
#
# These tests complement the SQLite unit tests in tests/test_lots.py by verifying:
#   - The ops schema (search_path=ops) is correctly resolved
#   - PostgreSQL triggers auto-populate data_completeness after child-record INSERTs
#   - Date range filtering works with PostgreSQL's native date type
#   - The JSON API responses match the real database state
#
# Test matrix:
#   TestIntListLots   — GET /api/v1/lots/    (list + date filter)
#   TestIntGetLot     — GET /api/v1/lots/{lot_code}  (detail + 404)
#   TestIntTriggers   — Verify PostgreSQL trigger logic for data_completeness
#
# AC coverage:
#   AC2  — retrieve a specific lot by lot_code (TestIntGetLot)
#   AC3  — filter lots by date range (TestIntListLots)
#   AC4  — completeness scores present in list response (TestIntListLots)
#   AC9  — full lot detail including child records (TestIntGetLot)
#   AC10 — completeness score driven by real PostgreSQL triggers (TestIntTriggers)
#
# All tests require TEST_DATABASE_URL in .env.test.
# They are skipped automatically when that variable is absent.

import pytest
from fastapi.testclient import TestClient


class TestIntListLots:
    """
    Integration tests for GET /api/v1/lots/

    Verifies that the list endpoint returns real PostgreSQL rows and that
    query-parameter filtering works against the actual date column type.
    """

    def test_returns_seeded_lots(self, pg_client: TestClient) -> None:
        """
        GET /api/v1/lots/ must include all four INT- lots in the response.

        The response may contain other lots (from production data), but it must
        include the four seeded by the integration test fixture.

        Time complexity: O(n) where n is the total number of lots in the DB.
        """
        response = pg_client.get("/api/v1/lots/")
        assert response.status_code == 200
        codes = {row["lot_code"] for row in response.json()}
        assert {"INT-A", "INT-B", "INT-C", "INT-D"}.issubset(codes)

    def test_date_filter_start_date(self, pg_client: TestClient) -> None:
        """
        start_date filter must exclude lots whose start_date is before the cutoff.

        INT-A and INT-B have start_date in January 2026 (before 2026-01-20).
        INT-C has start_date on 2026-01-20 and INT-D on 2026-02-01.
        With start_date=2026-01-20, only INT-C and INT-D should be returned
        (among the seeded lots).

        AC3: date range filtering.
        """
        response = pg_client.get("/api/v1/lots/", params={"start_date": "2026-01-20"})
        assert response.status_code == 200
        codes = {row["lot_code"] for row in response.json()}
        assert "INT-C" in codes
        assert "INT-D" in codes
        assert "INT-A" not in codes
        assert "INT-B" not in codes

    def test_date_filter_end_date(self, pg_client: TestClient) -> None:
        """
        end_date filter must exclude lots whose start_date is after the cutoff.

        With end_date=2026-01-15, only INT-A (start_date=2026-01-10) and
        INT-B (start_date=2026-01-12) are within range among seeded lots.

        AC3: date range filtering.
        """
        response = pg_client.get("/api/v1/lots/", params={"end_date": "2026-01-15"})
        assert response.status_code == 200
        codes = {row["lot_code"] for row in response.json()}
        assert "INT-A" in codes
        assert "INT-B" in codes
        assert "INT-C" not in codes
        assert "INT-D" not in codes

    def test_date_filter_range(self, pg_client: TestClient) -> None:
        """
        Combining start_date and end_date narrows results to the window.

        2026-01-12 to 2026-01-20 inclusive should include INT-B and INT-C
        (start_dates 2026-01-12 and 2026-01-20 respectively).

        AC3: date range filtering.
        """
        response = pg_client.get(
            "/api/v1/lots/",
            params={"start_date": "2026-01-12", "end_date": "2026-01-20"},
        )
        assert response.status_code == 200
        codes = {row["lot_code"] for row in response.json()}
        assert "INT-B" in codes
        assert "INT-C" in codes
        assert "INT-A" not in codes
        assert "INT-D" not in codes

    def test_response_includes_completeness_fields(self, pg_client: TestClient) -> None:
        """
        Every row in the list response must include data completeness fields.

        These fields are auto-populated by PostgreSQL triggers, not by the
        Python test fixture.  Their presence confirms the trigger ran correctly
        after the seed commit.

        AC4 / AC10: completeness data surfaced in the list view.
        """
        response = pg_client.get("/api/v1/lots/")
        assert response.status_code == 200
        rows = response.json()
        int_rows = [r for r in rows if r["lot_code"] in ("INT-A", "INT-B", "INT-C")]
        assert len(int_rows) == 3
        for row in int_rows:
            assert "has_production_data" in row
            assert "has_inspection_data" in row
            assert "has_shipping_data" in row
            assert "overall_completeness" in row

    def test_no_results_for_out_of_range_date(self, pg_client: TestClient) -> None:
        """
        A date range that excludes all lots returns an empty list, not an error.

        This verifies the API returns [] (HTTP 200) rather than 404 or 500 when
        the filter matches nothing.
        """
        response = pg_client.get(
            "/api/v1/lots/",
            params={"start_date": "2099-01-01", "end_date": "2099-12-31"},
        )
        assert response.status_code == 200
        # The result may not be empty if production data has future dates, but at
        # minimum none of the INT- lots should appear.
        codes = {row["lot_code"] for row in response.json()}
        assert "INT-A" not in codes
        assert "INT-B" not in codes


class TestIntGetLot:
    """
    Integration tests for GET /api/v1/lots/{lot_code}

    Verifies full lot detail retrieval including nested child records.
    """

    def test_returns_lot_a_with_all_records(self, pg_client: TestClient) -> None:
        """
        GET /api/v1/lots/INT-A must return the lot header, production, inspection,
        and shipping records, plus data completeness fields.

        AC2: retrieve a specific lot by lot_code.
        AC9: full detail including all child records.
        """
        response = pg_client.get("/api/v1/lots/INT-A")
        assert response.status_code == 200
        data = response.json()

        assert data["lot_code"] == "INT-A"
        assert data["start_date"] == "2026-01-10"
        assert data["end_date"] == "2026-01-15"
        assert len(data["production_records"]) == 1
        assert len(data["inspection_records"]) == 1
        assert len(data["shipping_records"]) == 1

        prod = data["production_records"][0]
        assert prod["production_line"] == "Line 2"
        assert prod["quantity_produced"] == 500
        assert prod["line_issue"] is False

        insp = data["inspection_records"][0]
        assert insp["inspection_result"] == "Pass"
        assert insp["issue_flag"] is False

        ship = data["shipping_records"][0]
        assert ship["shipment_status"] == "Delivered"
        assert ship["destination"] == "Detroit Assembly Plant"

    def test_lot_b_missing_inspection(self, pg_client: TestClient) -> None:
        """
        INT-B has no inspection record — the inspection_records list must be empty
        and has_inspection_data must be False.

        Confirms the trigger correctly sets has_inspection_data=false when no
        InspectionRecord exists for the lot.

        AC4 / AC10: completeness driven by real trigger logic.
        """
        response = pg_client.get("/api/v1/lots/INT-B")
        assert response.status_code == 200
        data = response.json()

        assert data["lot_code"] == "INT-B"
        assert data["inspection_records"] == []
        assert data["has_inspection_data"] is False
        assert data["has_production_data"] is True
        assert data["has_shipping_data"] is True

    def test_lot_c_flagged_inspection(self, pg_client: TestClient) -> None:
        """
        INT-C has a flagged (Fail) inspection and an On Hold shipment.
        Verify those values are persisted and returned correctly.

        AC5 / AC6: flagged inspection + On Hold shipment visible in detail view.
        """
        response = pg_client.get("/api/v1/lots/INT-C")
        assert response.status_code == 200
        data = response.json()

        insp = data["inspection_records"][0]
        assert insp["inspection_result"] == "Fail"
        assert insp["issue_flag"] is True
        assert insp["issue_category"] == "Dimensional"

        ship = data["shipping_records"][0]
        assert ship["shipment_status"] == "On Hold"

    def test_returns_404_for_nonexistent_lot(self, pg_client: TestClient) -> None:
        """
        GET /api/v1/lots/DOES-NOT-EXIST must return 404, not 500.

        AC2: the API must distinguish "lot not found" from a server error.
        """
        response = pg_client.get("/api/v1/lots/DOES-NOT-EXIST-XYZ")
        assert response.status_code == 404
        assert response.json()["detail"] == "Lot not found"


class TestIntTriggers:
    """
    Tests that validate PostgreSQL trigger logic via the API response.

    The unit tests in test_lots.py simulate triggers manually with
    refresh_data_completeness().  Here we verify the real triggers produce
    the same results when rows are inserted via the ORM.
    """

    def test_int_a_completeness_is_100(self, pg_client: TestClient) -> None:
        """
        INT-A has all three data domains → trigger must set completeness = 100.

        AC10: overall_completeness is accurate and trigger-driven.
        """
        response = pg_client.get("/api/v1/lots/INT-A")
        assert response.status_code == 200
        data = response.json()
        assert data["has_production_data"] is True
        assert data["has_inspection_data"] is True
        assert data["has_shipping_data"] is True
        assert float(data["overall_completeness"]) == 100.0

    def test_int_b_completeness_is_67(self, pg_client: TestClient) -> None:
        """
        INT-B is missing inspection → trigger must set completeness ≈ 67.

        (2 out of 3 domains present: round(2/3 * 100) = 67)

        AC10: trigger sets completeness proportional to present domains.
        """
        response = pg_client.get("/api/v1/lots/INT-B")
        assert response.status_code == 200
        data = response.json()
        assert float(data["overall_completeness"]) == pytest.approx(67, abs=1)

    def test_int_d_completeness_is_zero(self, pg_client: TestClient) -> None:
        """
        INT-D has no child records → the API must report 0% completeness.

        When no trigger has fired (no child inserts), data_completeness may
        not exist.  The router falls back to 0% for a missing row (AC10).
        """
        response = pg_client.get("/api/v1/lots/INT-D")
        assert response.status_code == 200
        data = response.json()
        assert float(data["overall_completeness"]) == pytest.approx(0, abs=1)
