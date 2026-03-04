-- ============================================================
-- Ops Analytics — Sample Queries
-- Mapped to Acceptance Criteria AC1–AC7
-- ============================================================


-- ============================================================
-- AC1 & AC2: All functions together by lot
-- Shows production, inspection, and shipping aligned by lot_id.
-- NOTE: Returns multiple rows per lot when a lot has more than
--       one record per function. Use AC7 for one-row-per-lot.
-- ============================================================
SELECT
    l.lot_id,
    l.start_date,
    l.end_date,
    p.production_date,
    p.production_line,
    p.quantity_produced,
    i.inspection_date,
    i.inspection_result,
    i.issue_flag,
    s.ship_date,
    s.shipment_status,
    s.destination,
    c.overall_completeness
FROM lots l
LEFT JOIN production_records p ON l.lot_id = p.lot_id
LEFT JOIN inspection_records i ON l.lot_id = i.lot_id
LEFT JOIN shipping_records   s ON l.lot_id = s.lot_id
JOIN  data_completeness      c ON l.lot_id = c.lot_id
WHERE l.lot_code = 'LOT-20260112-001';


-- ============================================================
-- AC3: Date range filter (refined — default)
-- Anchors on lots.start_date so incomplete lots (missing
-- production/inspection/shipping records) still appear with
-- NULLs in child columns. Supports AC4 and AC10 by making
-- gaps visible rather than silently dropping the lot.
-- ============================================================
SELECT
    l.lot_id,
    l.start_date,
    l.end_date,
    p.production_date,
    p.production_line,
    p.quantity_produced,
    i.inspection_result,
    i.issue_flag,
    s.shipment_status
FROM lots l
LEFT JOIN production_records p ON l.lot_id = p.lot_id
LEFT JOIN inspection_records i ON l.lot_id = i.lot_id
LEFT JOIN shipping_records   s ON l.lot_id = s.lot_id
WHERE l.start_date BETWEEN '2026-01-01' AND '2026-01-31';


-- ============================================================
-- AC3: Date range filter (alternative — production-only)
-- Use this when the analyst specifically wants confirmed
-- production output for a period, not lot activity overall.
-- NOTE: Lots with no production records yet are excluded.
-- ============================================================
-- SELECT
--     l.lot_id,
--     p.production_date,
--     p.production_line,
--     p.quantity_produced,
--     i.inspection_result,
--     i.issue_flag,
--     s.shipment_status
-- FROM lots l
-- LEFT JOIN production_records p ON l.lot_id = p.lot_id
-- LEFT JOIN inspection_records i ON l.lot_id = i.lot_id
-- LEFT JOIN shipping_records   s ON l.lot_id = s.lot_id
-- WHERE p.production_date BETWEEN '2026-01-01' AND '2026-01-31';


-- ============================================================
-- AC4 & AC10: Lots with missing data
-- Surfaces any lot not at 100% completeness so the analyst
-- knows which records are incomplete before a meeting.
-- ============================================================
SELECT
    l.lot_id,
    l.start_date,
    l.end_date,
    c.has_production_data,
    c.has_inspection_data,
    c.has_shipping_data,
    c.overall_completeness
FROM lots l
JOIN data_completeness c ON l.lot_id = c.lot_id
WHERE c.overall_completeness < 100
ORDER BY c.overall_completeness ASC;


-- ============================================================
-- AC5: Which production lines had the most issues
-- Joins production and inspection to calculate issue rate
-- per line. NULLIF guards against division by zero.
-- ============================================================
SELECT
    p.production_line,
    COUNT(*)                                                      AS total_inspections,
    SUM(CASE WHEN i.issue_flag THEN 1 ELSE 0 END)                AS total_issues,
    ROUND(
        SUM(CASE WHEN i.issue_flag THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    )                                                             AS issue_rate_pct
FROM production_records p
JOIN inspection_records i ON p.lot_id = i.lot_id
GROUP BY p.production_line
ORDER BY total_issues DESC;


-- ============================================================
-- AC6: Lots with inspection issues and their shipment status
-- LEFT JOIN on shipping ensures flagged lots with no shipment
-- record still appear, making the gap visible.
-- ============================================================
SELECT
    l.lot_id,
    i.inspection_result,
    i.issue_flag,
    s.shipment_status,
    s.ship_date,
    s.destination
FROM lots l
JOIN inspection_records i ON l.lot_id = i.lot_id
LEFT JOIN shipping_records s ON l.lot_id = s.lot_id
WHERE i.issue_flag = TRUE
ORDER BY l.lot_id, s.ship_date;


-- ============================================================
-- AC7: Meeting-ready operational summary (one row per lot)
-- Aggregates all functions into a single row per lot.
-- Use this as the primary view for meeting discussions.
-- ============================================================
SELECT
    l.lot_id,
    l.start_date,
    l.end_date,
    SUM(p.quantity_produced)                          AS total_produced,
    STRING_AGG(DISTINCT p.production_line, ', ')      AS lines_used,
    BOOL_OR(i.issue_flag)                             AS any_issues,
    COUNT(*) FILTER (WHERE i.issue_flag)              AS issue_count,
    MAX(s.shipment_status)                            AS latest_status,
    c.overall_completeness
FROM lots l
LEFT JOIN production_records p ON l.lot_id = p.lot_id
LEFT JOIN inspection_records i ON l.lot_id = i.lot_id
LEFT JOIN shipping_records   s ON l.lot_id = s.lot_id
JOIN  data_completeness      c ON l.lot_id = c.lot_id
GROUP BY l.lot_id, l.start_date, l.end_date, c.overall_completeness
ORDER BY l.lot_id;