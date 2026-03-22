# tests/test_lots.py
#
# Unit tests for the lots API endpoints.
#
# Endpoints under test:
#   GET /api/v1/lots/             → list_lots()
#   GET /api/v1/lots/{lot_code}   → get_lot()
#
# AC coverage:
#   AC2  — retrieve a specific lot by lot_code
#   AC3  — date range filtering
#   AC4  — completeness flags in list response
#   AC9  — full detail view (child records included)
#   AC10 — completeness score in list response
#
# Test naming convention:
#   test_<endpoint>_<scenario>
#
# All tests use the `client` fixture (conftest.py) which provides a TestClient
# backed by an in-memory SQLite database with no data unless `seeded_db` is used.

from fastapi.testclient import TestClient

# ── GET /api/v1/lots/ ─────────────────────────────────────────────────────────


class TestListLots:
    """Tests for GET /api/v1/lots/ (list endpoint)."""

    def test_list_lots_returns_200_with_empty_list(self, client: TestClient) -> None:
        """
        When the database has no lots, the endpoint should return HTTP 200
        with an empty JSON array [].

        AC: Baseline — API is reachable and returns a valid empty response.
        """
        response = client.get("/api/v1/lots/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_lots_returns_all_lots_without_filter(self, client: TestClient, seeded_db) -> None:
        """
        When no date filter is applied, all four seeded lots are returned.

        AC2: All lots are visible in the list.
        """
        response = client.get("/api/v1/lots/")
        assert response.status_code == 200
        assert len(response.json()) == 4

    def test_list_lots_date_filter_start_date(self, client: TestClient, seeded_db) -> None:
        """
        When start_date=2026-02-01, only LOT-D (start_date=2026-02-01) is returned.
        LOT-A, LOT-B, LOT-C (all January) are excluded.

        AC3: Date filtering on lots.start_date lower bound.
        """
        response = client.get("/api/v1/lots/?start_date=2026-02-01")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["lot_code"] == "LOT-D"

    def test_list_lots_date_filter_range(self, client: TestClient, seeded_db) -> None:
        """
        When start_date=2026-01-01 and end_date=2026-01-31, only January lots returned.
        LOT-D (February) is excluded.

        AC3: Date filtering with both bounds.
        """
        response = client.get("/api/v1/lots/?start_date=2026-01-01&end_date=2026-01-31")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        lot_codes = {row["lot_code"] for row in data}
        assert lot_codes == {"LOT-A", "LOT-B", "LOT-C"}

    def test_list_lots_includes_completeness_score(self, client: TestClient, seeded_db) -> None:
        """
        Each row in the response must include overall_completeness,
        has_production_data, has_inspection_data, has_shipping_data.

        AC4/AC10: Completeness data visible in the list view.
        """
        response = client.get("/api/v1/lots/")
        assert response.status_code == 200
        rows = response.json()
        # Verify the first row has all completeness fields
        assert "overall_completeness" in rows[0]
        assert "has_production_data" in rows[0]
        assert "has_inspection_data" in rows[0]
        assert "has_shipping_data" in rows[0]
        # LOT-D has no child records → completeness = 0
        lot_d = next(r for r in rows if r["lot_code"] == "LOT-D")
        assert float(lot_d["overall_completeness"]) == 0

    def test_list_lots_lot_b_has_correct_completeness(self, client: TestClient, seeded_db) -> None:
        """
        LOT-B has production and shipping but no inspection → completeness = 67.

        AC10: Partial completeness score is correctly calculated.
        """
        response = client.get("/api/v1/lots/")
        assert response.status_code == 200
        lot_b = next(r for r in response.json() if r["lot_code"] == "LOT-B")
        assert float(lot_b["overall_completeness"]) == 67
        assert lot_b["has_production_data"] is True
        assert lot_b["has_inspection_data"] is False
        assert lot_b["has_shipping_data"] is True


# ── GET /api/v1/lots/{lot_code} ───────────────────────────────────────────────


class TestGetLot:
    """Tests for GET /api/v1/lots/{lot_code} (detail endpoint)."""

    def test_get_lot_returns_404_for_unknown_code(self, client: TestClient) -> None:
        """
        When the lot_code does not exist, the endpoint returns HTTP 404.

        AC2: Graceful not-found handling.
        """
        response = client.get("/api/v1/lots/LOT-DOES-NOT-EXIST")
        assert response.status_code == 404

    def test_get_lot_returns_lot_a_with_all_child_records(
        self, client: TestClient, seeded_db
    ) -> None:
        """
        GET /api/v1/lots/LOT-A returns 200 with all three child record types populated.

        AC9: Full detail view includes production, inspection, and shipping records.
        """
        response = client.get("/api/v1/lots/LOT-A")
        assert response.status_code == 200
        data = response.json()
        assert data["lot_code"] == "LOT-A"
        assert len(data["production_records"]) == 1
        assert len(data["inspection_records"]) == 1
        assert len(data["shipping_records"]) == 1

    def test_get_lot_lot_c_has_flagged_inspection(self, client: TestClient, seeded_db) -> None:
        """
        LOT-C's inspection record has issue_flag=True and issue_category='Dimensional'.

        AC5: Inspection issue visible in lot detail.
        AC6: LOT-C has On Hold shipping — linked to the flagged inspection.
        """
        response = client.get("/api/v1/lots/LOT-C")
        assert response.status_code == 200
        data = response.json()
        insp = data["inspection_records"][0]
        assert insp["issue_flag"] is True
        assert insp["issue_category"] == "Dimensional"
        ship = data["shipping_records"][0]
        assert ship["shipment_status"] == "On Hold"

    def test_get_lot_d_has_empty_child_record_lists(self, client: TestClient, seeded_db) -> None:
        """
        LOT-D has no production, inspection, or shipping records.
        Child record lists must be empty [], not missing from the response.

        AC4: Missing data is surfaced (empty lists, not nulls).
        """
        response = client.get("/api/v1/lots/LOT-D")
        assert response.status_code == 200
        data = response.json()
        assert data["production_records"] == []
        assert data["inspection_records"] == []
        assert data["shipping_records"] == []
        assert float(data["overall_completeness"]) == 0
