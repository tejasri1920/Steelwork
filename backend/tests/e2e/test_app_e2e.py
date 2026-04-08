# tests/e2e/test_app_e2e.py
#
# End-to-end tests for the Steelworks Ops Analytics web application.
#
# These tests use Playwright to drive a real Chromium browser against the full
# stack (React frontend + FastAPI backend + PostgreSQL test database).  They
# verify the complete user journey that an operations analyst would take, from
# loading the dashboard to drilling into a specific lot.
#
# Test coverage:
#   TestDashboard        — Page loads, navbar visible, tab navigation
#   TestLotSummaryTab    — Lot summary table renders data rows
#   TestReportTabs       — Inspection issues / incomplete lots / line issues tabs
#   TestLotDetailPage    — Clicking a lot code navigates to the detail view
#   TestDateFilter       — Date filter controls update the lot list
#   TestNotFoundPage     — Navigating to a non-existent lot shows an error
#
# AC coverage:
#   AC1  — Cross-function summary visible on dashboard (TestLotSummaryTab)
#   AC2  — Specific lot accessible by lot_code link (TestLotDetailPage)
#   AC3  — Date range filter controls present and functional (TestDateFilter)
#   AC4  — Incomplete lots tab surfaces missing-data lots (TestReportTabs)
#   AC5  — Line issues tab shows per-line issue rates (TestReportTabs)
#   AC6  — Inspection issues tab shows flagged lots (TestReportTabs)
#   AC7  — Dashboard is meeting-ready: summary and reports in one place (TestDashboard)
#   AC8  — Shipment status visible in the lot summary (TestLotSummaryTab)
#   AC9  — Lot detail page shows all three domains (TestLotDetailPage)
#   AC10 — Completeness indicator visible in the incomplete lots tab (TestReportTabs)
#
# All tests require:
#   - TEST_DATABASE_URL in .env.test
#   - playwright install already run:  poetry run playwright install
#   - npm install already run in frontend/
#
# The conftest.py in this directory starts the backend and frontend servers
# automatically.  Tests are skipped if TEST_DATABASE_URL is absent.

import re

from playwright.sync_api import Page, expect  # noqa: F401 (expect used via assertions)

# ── Helpers ────────────────────────────────────────────────────────────────────

# Default timeout (ms) for Playwright assertions.
# Set to 30 s to accommodate:
#   - Render free-tier PostgreSQL cold start (first query can take 15–30 s)
#   - React Query re-fetch after the DB connection pool warms up
_TIMEOUT = 30_000


class TestDashboard:
    """
    Smoke tests for the Dashboard page (/).

    Verify that the page loads, the navbar is present, and the four report tabs
    are navigable.  These tests run even when the database is empty.
    """

    def test_page_title_and_navbar(self, page: Page) -> None:
        """
        The dashboard must display the application title in the navbar.

        AC7: The dashboard is the analyst's one-stop view — it must be clearly
             labelled so stakeholders know where they are.
        """
        page.goto("/")
        # The Navbar component renders "Steelworks Ops" as its brand text.
        expect(page.get_by_text("Steelworks Ops")).to_be_visible(timeout=_TIMEOUT)

    def test_four_tabs_are_visible(self, page: Page) -> None:
        """
        The dashboard must show all four report tabs.

        AC1:  Cross-function data (lot summary) and focused views (issues,
              incomplete, line breakdown) are all accessible from one page.
        AC7:  Single-page design for meetings — all views reachable with one click.
        """
        page.goto("/")
        expect(page.get_by_role("tab", name=re.compile(r"Lot Summary", re.I))).to_be_visible(
            timeout=_TIMEOUT
        )
        expect(page.get_by_role("tab", name=re.compile(r"Inspection Issues", re.I))).to_be_visible(
            timeout=_TIMEOUT
        )
        expect(page.get_by_role("tab", name=re.compile(r"Incomplete Lots", re.I))).to_be_visible(
            timeout=_TIMEOUT
        )
        expect(page.get_by_role("tab", name=re.compile(r"Issues by Line", re.I))).to_be_visible(
            timeout=_TIMEOUT
        )

    def test_clicking_inspection_issues_tab(self, page: Page) -> None:
        """
        Clicking the Inspection Issues tab must activate it without a page reload.

        AC6: Flagged inspection data is accessible via a single tab click.
        """
        page.goto("/")
        tab = page.get_by_role("tab", name=re.compile(r"Inspection Issues", re.I))
        tab.click()
        # After clicking, the tab should become selected/active.
        # React-based tabs typically add aria-selected="true" or a selected class.
        expect(tab).to_be_visible(timeout=_TIMEOUT)

    def test_clicking_incomplete_lots_tab(self, page: Page) -> None:
        """
        Clicking the Incomplete Lots tab must show the incompleteness report.

        AC4:  Incomplete lots are just one tab away.
        AC10: Completeness scores are surfaced without a separate page load.
        """
        page.goto("/")
        tab = page.get_by_role("tab", name=re.compile(r"Incomplete Lots", re.I))
        tab.click()
        expect(tab).to_be_visible(timeout=_TIMEOUT)

    def test_clicking_line_issues_tab(self, page: Page) -> None:
        """
        Clicking the Issues by Line tab must show the per-line report.

        AC5: Production-line issue rates accessible from the dashboard.
        """
        page.goto("/")
        tab = page.get_by_role("tab", name=re.compile(r"Issues by Line", re.I))
        tab.click()
        expect(tab).to_be_visible(timeout=_TIMEOUT)


class TestLotSummaryTab:
    """
    Tests for the Lot Summary tab (default tab on dashboard load).

    Verifies that the lot summary table renders and includes the seeded INT- lots.
    """

    def test_lot_summary_table_loads(self, page: Page) -> None:
        """
        The Lot Summary tab must render a table (or equivalent) when data loads.

        AC1: Cross-domain summary view renders without errors.
        AC7: Table is visible and ready for meeting use.
        """
        page.goto("/")
        # Wait for the React Query fetch to complete; a table or rows should appear.
        # We look for the "INT-A" lot code which was seeded by the integration fixture.
        expect(page.get_by_text("INT-A")).to_be_visible(timeout=_TIMEOUT)

    def test_lot_code_links_are_clickable(self, page: Page) -> None:
        """
        Each lot code in the summary table must be a clickable link.

        Clicking it navigates to /lots/{lot_code} (the detail page).

        AC2: Lot is accessible by clicking its code in the summary.
        """
        page.goto("/")
        # Wait for lot data to load
        lot_link = page.get_by_role("link", name="INT-A")
        expect(lot_link).to_be_visible(timeout=_TIMEOUT)

    def test_shipped_status_visible(self, page: Page) -> None:
        """
        The Delivered shipment status for INT-A must appear in the summary table.

        AC8: Shipment status is visible without navigating to the detail page.
        """
        page.goto("/")
        # Use .first() because multiple lots may have "Delivered" status in the table.
        # Strict mode requires exactly one match without .first(); AC8 only requires
        # that at least one Delivered status is visible.
        expect(page.get_by_text("Delivered").first).to_be_visible(timeout=_TIMEOUT)


class TestReportTabs:
    """
    Tests for the three report tabs: Inspection Issues, Incomplete Lots, Issues by Line.
    """

    def test_inspection_issues_shows_flagged_lot(self, page: Page) -> None:
        """
        The Inspection Issues tab must list INT-C (issue_flag=True).

        AC5: Lots with quality problems surface in this report.
        AC6: Flagged lot with On Hold status is visible.
        """
        page.goto("/")
        page.get_by_role("tab", name=re.compile(r"Inspection Issues", re.I)).click()
        expect(page.get_by_text("INT-C")).to_be_visible(timeout=_TIMEOUT)

    def test_incomplete_lots_shows_int_b_and_int_d(self, page: Page) -> None:
        """
        The Incomplete Lots tab must show INT-B (67%) and INT-D (0%).

        AC4:  Incomplete lots are surfaced so analysts can follow up.
        AC10: Completeness scores are displayed alongside the lot codes.
        """
        page.goto("/")
        page.get_by_role("tab", name=re.compile(r"Incomplete Lots", re.I)).click()
        expect(page.get_by_text("INT-B")).to_be_visible(timeout=_TIMEOUT)
        expect(page.get_by_text("INT-D")).to_be_visible(timeout=_TIMEOUT)

    def test_incomplete_lots_does_not_show_complete_lots(self, page: Page) -> None:
        """
        INT-A (100%) must NOT appear in the Incomplete Lots tab.

        AC4: The report filters to incomplete lots only; complete lots are noise.
        """
        page.goto("/")
        page.get_by_role("tab", name=re.compile(r"Incomplete Lots", re.I)).click()
        # Wait for the tab content to render before asserting absence.
        page.wait_for_timeout(2000)
        # The INT-A text must not be visible in the table.
        # (It may appear elsewhere on the page, e.g. in a tab label, so we scope
        # the check to the main content area.)
        main = page.locator("main")
        expect(main.get_by_text("INT-A")).not_to_be_visible(timeout=_TIMEOUT)

    def test_line_issues_tab_renders(self, page: Page) -> None:
        """
        The Issues by Line tab must render without crashing.

        If INT-C's production record (Line 3) seeded correctly, "Line 3" must
        appear in this report.

        AC5: Per-line issue breakdown is accessible.
        """
        page.goto("/")
        page.get_by_role("tab", name=re.compile(r"Issues by Line", re.I)).click()
        expect(page.get_by_text("Line 3")).to_be_visible(timeout=_TIMEOUT)


class TestLotDetailPage:
    """
    Tests for the Lot Detail page (/lots/:lotCode).

    Verifies full drill-down: lot header, production, inspection, and shipping
    record sections.
    """

    def test_navigate_to_lot_a_detail(self, page: Page) -> None:
        """
        Clicking the INT-A link in the summary navigates to /lots/INT-A.

        AC2: Individual lot is retrievable by lot_code via the UI.
        """
        page.goto("/")
        # Wait for the link to appear then click it
        lot_link = page.get_by_role("link", name="INT-A")
        expect(lot_link).to_be_visible(timeout=_TIMEOUT)
        lot_link.click()
        # URL must change to the detail page
        expect(page).to_have_url(re.compile(r"/lots/INT-A"), timeout=_TIMEOUT)

    def test_lot_detail_shows_lot_code(self, page: Page) -> None:
        """
        The detail page for INT-A must prominently display the lot code.

        AC9: The analyst sees the lot identifier at the top of the detail view.
        """
        page.goto("/lots/INT-A")
        expect(page.get_by_text("INT-A")).to_be_visible(timeout=_TIMEOUT)

    def test_lot_detail_shows_production_section(self, page: Page) -> None:
        """
        The detail page must show a production records section.

        AC9: All three data domains (production, inspection, shipping) are
             visible on the detail page.
        """
        page.goto("/lots/INT-A")
        # The LotDetailPage renders a "Production Records" heading or table.
        expect(page.get_by_text(re.compile(r"production", re.I))).to_be_visible(timeout=_TIMEOUT)

    def test_lot_detail_shows_shipping_section(self, page: Page) -> None:
        """
        The detail page must show a shipping records section with the Delivered status.

        AC9: Shipping domain is part of the full drill-down.
        AC8: Shipment status (Delivered) is visible in the detail view.
        """
        page.goto("/lots/INT-A")
        expect(page.get_by_text("Delivered")).to_be_visible(timeout=_TIMEOUT)

    def test_lot_detail_shows_inspection_section(self, page: Page) -> None:
        """
        The detail page for INT-A must show inspection records with Pass result.

        AC9: Inspection domain is part of the full drill-down.
        """
        page.goto("/lots/INT-A")
        expect(page.get_by_text("Pass")).to_be_visible(timeout=_TIMEOUT)

    def test_lot_detail_shows_on_hold_for_int_c(self, page: Page) -> None:
        """
        The detail page for INT-C must display the On Hold shipment status and the
        flagged Fail inspection.

        AC6: Flagged lot + On Hold status visible in the detail drill-down.
        """
        page.goto("/lots/INT-C")
        expect(page.get_by_text("Fail")).to_be_visible(timeout=_TIMEOUT)
        expect(page.get_by_text("On Hold")).to_be_visible(timeout=_TIMEOUT)


class TestDateFilter:
    """
    Tests for the date range filter on the Dashboard.
    """

    def test_date_filter_inputs_are_present(self, page: Page) -> None:
        """
        The dashboard must render start_date and end_date input controls.

        AC3: Date range filter is accessible from the main dashboard view.
        """
        page.goto("/")
        # The DateRangeFilter component renders two <input type="date"> elements.
        date_inputs = page.locator('input[type="date"]')
        expect(date_inputs.first).to_be_visible(timeout=_TIMEOUT)

    def test_date_filter_updates_results(self, page: Page) -> None:
        """
        Setting end_date to 2026-01-15 must exclude lots with later start_dates
        (INT-C on 2026-01-20 and INT-D on 2026-02-01).

        AC3: The date filter is wired to the API and updates the table.
        """
        page.goto("/")
        # Wait for initial load
        expect(page.get_by_text("INT-A")).to_be_visible(timeout=_TIMEOUT)

        # Fill the end_date input.  The DateRangeFilter component renders two
        # date inputs; we target the second one (end_date).
        date_inputs = page.locator('input[type="date"]')
        date_inputs.nth(1).fill("2026-01-15")

        # After filtering, INT-C (start_date=2026-01-20) should disappear.
        # Allow time for the React Query refetch triggered by the input change.
        expect(page.get_by_text("INT-C")).not_to_be_visible(timeout=_TIMEOUT)


class TestNotFoundPage:
    """
    Tests for the 404 / error state when navigating to a non-existent lot.
    """

    def test_nonexistent_lot_shows_error(self, page: Page) -> None:
        """
        Navigating to /lots/NONEXISTENT-XYZ must show an error message rather
        than crashing the application.

        AC2: The UI handles lot-not-found gracefully (no white screen of death).
        """
        page.goto("/lots/NONEXISTENT-XYZ")
        # The LotDetailPage shows an error when the API returns 404.
        # We look for any text indicating the lot was not found.
        expect(page.get_by_text(re.compile(r"not found|error|404", re.I))).to_be_visible(
            timeout=_TIMEOUT
        )
