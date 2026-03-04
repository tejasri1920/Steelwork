-- ---------------------------------------------------------------------------
-- 0. SCHEMA
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS ops;
SET search_path TO ops, public;


-- ---------------------------------------------------------------------------
-- 1. ENUM TYPES
--    Derived from all distinct values observed in the Excel source data.
--    Preferred over VARCHAR+CHECK: self-documenting, type-safe,
--    case-sensitive by definition, visible in schema introspection tools.
-- ---------------------------------------------------------------------------

-- Production
CREATE TYPE ops.shift_type AS ENUM ('Day', 'Swing', 'Night');

CREATE TYPE ops.production_line_type AS ENUM ('Line 1', 'Line 2', 'Line 3', 'Line 4');

CREATE TYPE ops.primary_issue_type AS ENUM (
    'Changeover delay',
    'Material shortage',
    'Operator training',
    'Quality hold',
    'Sensor fault',
    'Tool wear'
);

-- Inspection
CREATE TYPE ops.inspection_result_type AS ENUM ('Pass', 'Fail', 'Conditional Pass');

-- Shipping
CREATE TYPE ops.shipment_status_type AS ENUM ('Shipped', 'Partial', 'On Hold', 'Backordered');

CREATE TYPE ops.carrier_type AS ENUM (
    'UPS Freight',
    'FedEx Freight',
    'XPO',
    'Old Dominion',
    'Local Truck'
);

CREATE TYPE ops.customer_type AS ENUM (
    'Acme Rail',
    'Midwest Conveyors',
    'NorthStar Ag',
    'Prairie Pumps',
    'Rivertown HVAC',
    'SteelWorks Internal'
);

CREATE TYPE ops.us_state_abbr AS ENUM ('IA', 'IL', 'IN', 'MI', 'OH', 'WI');


-- ---------------------------------------------------------------------------
-- 2. LOTS
--    Central entity. Every child table references lot_id.
--
--    lot_code : canonical business identifier (e.g. LOT-20260112-001).
--               Source spreadsheets contain inconsistently formatted lot
--               strings; normalisation happens at ETL before insert.
--    end_date : nullable — a lot that is still open has no closing date yet.
--               Making it NOT NULL would require a dummy future date, which
--               is worse than NULL.
-- ---------------------------------------------------------------------------
CREATE TABLE ops.lots (
    lot_id      SERIAL          PRIMARY KEY,
    lot_code    VARCHAR(50)     NOT NULL,
    start_date  DATE            NOT NULL,
    end_date    DATE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_lots_lot_code
        UNIQUE (lot_code),
    CONSTRAINT chk_lots_dates
        CHECK (end_date IS NULL OR end_date >= start_date)
);

COMMENT ON TABLE  ops.lots IS 'Master lot registry. One row per production lot.';
COMMENT ON COLUMN ops.lots.lot_code   IS 'Canonical business identifier, e.g. LOT-20260112-001. Normalised at ETL from inconsistent source strings.';
COMMENT ON COLUMN ops.lots.start_date IS 'Date the lot was opened / first produced.';
COMMENT ON COLUMN ops.lots.end_date   IS 'Date the lot was closed. NULL while the lot is still open.';

CREATE INDEX idx_lots_dates ON ops.lots (start_date, end_date);


-- ---------------------------------------------------------------------------
-- 3. PRODUCTION_RECORDS
--    One row per production run (unique combination of lot + date + shift + line).
--    Supports AC1, AC2, AC3, AC5.
-- ---------------------------------------------------------------------------
CREATE TABLE ops.production_records (
    production_id     SERIAL                    PRIMARY KEY,

    -- Relationship
    lot_id            INTEGER                   NOT NULL
                          REFERENCES ops.lots (lot_id)
                          ON DELETE RESTRICT
                          ON UPDATE CASCADE,

    -- Core fields (logical design)
    production_date   DATE                      NOT NULL,
    production_line   ops.production_line_type  NOT NULL,
    quantity_produced INTEGER                   NOT NULL CHECK (quantity_produced >= 0),

    -- Operational fields (from Ops_Production_Log.xlsx)
    shift             ops.shift_type            NOT NULL,
    part_number       VARCHAR(20)               NOT NULL,
    units_planned     INTEGER                   NOT NULL CHECK (units_planned >= 0),
    downtime_min      SMALLINT                  NOT NULL DEFAULT 0 CHECK (downtime_min >= 0),
    line_issue        BOOLEAN                   NOT NULL DEFAULT FALSE,
    primary_issue     ops.primary_issue_type,             -- NULL when line_issue = FALSE
    supervisor_notes  TEXT,

    -- Audit
    created_at        TIMESTAMPTZ               NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ               NOT NULL DEFAULT now(),

    -- A lot cannot have two runs on the same date, shift, and line
    CONSTRAINT uq_production_run
        UNIQUE (lot_id, production_date, shift, production_line),

    -- primary_issue only valid when a line issue has been flagged
    CONSTRAINT chk_prod_issue_consistency
        CHECK (primary_issue IS NULL OR line_issue = TRUE)
);

COMMENT ON TABLE  ops.production_records IS 'One production run per row. Sourced from Ops_Production_Log.xlsx.';
COMMENT ON COLUMN ops.production_records.quantity_produced IS 'Actual units produced ("Units Actual" in source spreadsheet).';
COMMENT ON COLUMN ops.production_records.line_issue        IS 'TRUE when a line issue was flagged ("Yes" in Line Issue? column).';

-- lot_id alone is the leading column of the composite index below,
-- so a separate single-column lot_id index is redundant and omitted.
CREATE INDEX idx_production_lot_date
    ON ops.production_records (lot_id, production_date);         -- lot JOINs + date-range filter (AC3)

CREATE INDEX idx_production_date
    ON ops.production_records (production_date);                 -- date-only filter without lot_id

CREATE INDEX idx_production_line
    ON ops.production_records (production_line);                 -- GROUP BY line (AC5 view)

CREATE INDEX idx_production_issue
    ON ops.production_records (line_issue)
    WHERE line_issue = TRUE;                                     -- partial: flagged runs only


-- ---------------------------------------------------------------------------
-- 4. INSPECTION_RECORDS
--    One row per inspection event for a lot.
--    Supports AC1, AC4, AC5.
-- ---------------------------------------------------------------------------
CREATE TABLE ops.inspection_records (
    inspection_id     SERIAL                        PRIMARY KEY,

    -- Relationship
    lot_id            INTEGER                       NOT NULL
                          REFERENCES ops.lots (lot_id)
                          ON DELETE RESTRICT
                          ON UPDATE CASCADE,

    -- Core fields (logical design)
    inspection_date   DATE                          NOT NULL,
    inspection_result ops.inspection_result_type    NOT NULL,
    issue_flag        BOOLEAN                       NOT NULL DEFAULT FALSE,

    -- Operational field
    inspector_notes   TEXT,

    -- Audit
    created_at        TIMESTAMPTZ                   NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ                   NOT NULL DEFAULT now()
);

COMMENT ON TABLE  ops.inspection_records IS 'Quality inspection events per lot.';
COMMENT ON COLUMN ops.inspection_records.issue_flag IS 'TRUE when the inspection identified a defect or concern (AC5).';

-- 3-column composite from peer DDL: covers lot JOINs, date-range filter,
-- and issue_flag filter together — better than three separate indexes.
CREATE INDEX idx_inspection_lot_date
    ON ops.inspection_records (lot_id, inspection_date, issue_flag);

CREATE INDEX idx_inspection_date
    ON ops.inspection_records (inspection_date);                  -- date-only filter without lot_id

CREATE INDEX idx_inspection_issue_flag
    ON ops.inspection_records (issue_flag)
    WHERE issue_flag = TRUE;                                      -- partial: flagged rows only (AC5)


-- ---------------------------------------------------------------------------
-- 5. SHIPPING_RECORDS
--    One row per shipment dispatch event. A lot may have multiple rows
--    (split shipments observed in source data).
--    Supports AC1, AC6.
-- ---------------------------------------------------------------------------
CREATE TABLE ops.shipping_records (
    shipping_id       SERIAL                      PRIMARY KEY,

    -- Relationship
    lot_id            INTEGER                     NOT NULL
                          REFERENCES ops.lots (lot_id)
                          ON DELETE RESTRICT
                          ON UPDATE CASCADE,

    -- Core fields (logical design)
    ship_date         DATE                        NOT NULL,
    shipment_status   ops.shipment_status_type    NOT NULL,
    destination       ops.us_state_abbr           NOT NULL,

    -- Operational fields (from Ops_Shipping_Log.xlsx)
    sales_order       VARCHAR(20),               -- nullable: one source row had no SO#
    customer          ops.customer_type           NOT NULL,
    carrier           ops.carrier_type,           -- nullable: some rows show customer pickup
    bol_number        VARCHAR(20)                 UNIQUE,         -- nullable UNIQUE: not every shipment has a BOL
    tracking_pro      VARCHAR(50),
    qty_shipped       INTEGER                     NOT NULL DEFAULT 0 CHECK (qty_shipped >= 0),
    hold_reason       VARCHAR(100),
    shipping_notes    TEXT,

    -- Audit
    created_at        TIMESTAMPTZ                 NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ                 NOT NULL DEFAULT now(),

    -- hold_reason is mandatory whenever a shipment is placed on hold (AC6)
    CONSTRAINT chk_ship_hold_reason
        CHECK (shipment_status != 'On Hold' OR hold_reason IS NOT NULL)
);

COMMENT ON TABLE  ops.shipping_records IS 'Outbound shipment records per lot. Sourced from Ops_Shipping_Log.xlsx. A lot may have multiple rows for split shipments.';
COMMENT ON COLUMN ops.shipping_records.bol_number  IS 'Bill of Lading number. UNIQUE per shipment; nullable because some rows have no BOL (e.g. customer pickup).';
COMMENT ON COLUMN ops.shipping_records.hold_reason IS 'Required when shipment_status = ''On Hold'' (enforced by chk_ship_hold_reason). Supports AC4, AC6.';

-- 3-column composite from peer DDL: covers lot JOINs, date-range filter,
-- and status filter in a single index — replaces three separate indexes.
CREATE INDEX idx_shipping_lot_date
    ON ops.shipping_records (lot_id, ship_date, shipment_status);

CREATE INDEX idx_shipping_ship_date
    ON ops.shipping_records (ship_date);                          -- date-only filter without lot_id

CREATE INDEX idx_shipping_customer
    ON ops.shipping_records (customer);                           -- customer-based filter

CREATE INDEX idx_shipping_destination
    ON ops.shipping_records (destination);                        -- destination-based filter


-- ---------------------------------------------------------------------------
-- 6. DATA_COMPLETENESS
--    One row per lot, automatically maintained by triggers.
--    Supports AC4, AC8, AC9, AC10.
--
--    overall_completeness : SMALLINT integer percentage (0, 33, 67, or 100).
--                           Integer over float per best practice.
--    ON DELETE CASCADE     : this is a derived summary row — it has no
--                           independent meaning and should be removed when
--                           its parent lot is deleted.
--    last_evaluated_at     : business-visible audit field; tells analysts
--                           when the completeness score was last recalculated.
-- ---------------------------------------------------------------------------
CREATE TABLE ops.data_completeness (
    lot_id                INTEGER     PRIMARY KEY
                              REFERENCES ops.lots (lot_id)
                              ON DELETE CASCADE
                              ON UPDATE CASCADE,
    has_production_data   BOOLEAN     NOT NULL DEFAULT FALSE,
    has_inspection_data   BOOLEAN     NOT NULL DEFAULT FALSE,
    has_shipping_data     BOOLEAN     NOT NULL DEFAULT FALSE,
    overall_completeness  SMALLINT    NOT NULL DEFAULT 0
                              CHECK (overall_completeness BETWEEN 0 AND 100),
    last_evaluated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  ops.data_completeness IS 'One row per lot summarising data availability across all three functions. Auto-maintained by triggers (AC4, AC10).';
COMMENT ON COLUMN ops.data_completeness.overall_completeness IS 'Integer percentage 0–100. Possible values: 0, 33, 67, 100. Stored as integer per best practice (not float).';
COMMENT ON COLUMN ops.data_completeness.last_evaluated_at    IS 'Timestamp of the last trigger-driven recalculation. Business-visible: tells analysts how fresh the completeness score is.';

-- Partial index: v_incomplete_lots always filters WHERE overall_completeness < 100
CREATE INDEX idx_completeness_incomplete
    ON ops.data_completeness (overall_completeness)
    WHERE overall_completeness < 100;


-- ---------------------------------------------------------------------------
-- 7. TRIGGER — updated_at auto-maintenance
--    Applies to the three record tables and lots.
--    data_completeness has no updated_at — it is trigger-managed;
--    last_evaluated_at already captures when it was last touched.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ops.fn_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_lots_updated_at
    BEFORE UPDATE ON ops.lots
    FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();

CREATE TRIGGER trg_production_updated_at
    BEFORE UPDATE ON ops.production_records
    FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();

CREATE TRIGGER trg_inspection_updated_at
    BEFORE UPDATE ON ops.inspection_records
    FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();

CREATE TRIGGER trg_shipping_updated_at
    BEFORE UPDATE ON ops.shipping_records
    FOR EACH ROW EXECUTE FUNCTION ops.fn_set_updated_at();


-- ---------------------------------------------------------------------------
-- 8. TRIGGER — initialise data_completeness when a new lot is created
--    Without this, brand-new lots with no child records yet would have no
--    row in data_completeness and would be invisible to v_incomplete_lots.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ops.fn_init_data_completeness()
RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
BEGIN
    INSERT INTO ops.data_completeness (lot_id)
    VALUES (NEW.lot_id)
    ON CONFLICT (lot_id) DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_lots_init_completeness
    AFTER INSERT ON ops.lots
    FOR EACH ROW EXECUTE FUNCTION ops.fn_init_data_completeness();


-- ---------------------------------------------------------------------------
-- 9. TRIGGER FUNCTION — recalculate data_completeness on any child change
--
--    Design decisions:
--    • TG_OP = 'DELETE' uses OLD.lot_id (NEW is NULL on delete).
--    • NULL guard on v_lot_id handles edge case of concurrent lot deletion.
--    • EXISTS halts at first matching row — avoids full COUNT(*) scan.
--    • ROUND(... * 100.0 / 3)::SMALLINT gives 0, 33, 67, 100 — correctly
--      rounds 2/3 to 67, not 66 (integer division would give 66).
--    • UPSERT pattern handles both first-time insert and subsequent updates.
--    • RETURN NULL is correct for AFTER triggers — return value is ignored
--      for statement execution but NULL is the conventional signal.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ops.fn_refresh_data_completeness()
RETURNS TRIGGER
LANGUAGE plpgsql AS
$$
DECLARE
    v_lot_id   INTEGER;
    v_has_prod BOOLEAN;
    v_has_insp BOOLEAN;
    v_has_ship BOOLEAN;
    v_score    SMALLINT;
BEGIN
    -- Resolve lot_id safely regardless of operation type
    v_lot_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.lot_id ELSE NEW.lot_id END;

    -- Guard against concurrent deletion of the parent lot
    IF v_lot_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- EXISTS stops at first match — no full table scan
    v_has_prod := EXISTS (SELECT 1 FROM ops.production_records WHERE lot_id = v_lot_id);
    v_has_insp := EXISTS (SELECT 1 FROM ops.inspection_records  WHERE lot_id = v_lot_id);
    v_has_ship := EXISTS (SELECT 1 FROM ops.shipping_records    WHERE lot_id = v_lot_id);

    -- ROUND ensures 2-of-3 = 67, not 66 (integer division truncates)
    v_score := ROUND(
        (v_has_prod::INT + v_has_insp::INT + v_has_ship::INT) * 100.0 / 3
    )::SMALLINT;

    INSERT INTO ops.data_completeness
        (lot_id, has_production_data, has_inspection_data, has_shipping_data,
         overall_completeness, last_evaluated_at)
    VALUES
        (v_lot_id, v_has_prod, v_has_insp, v_has_ship, v_score, now())
    ON CONFLICT (lot_id) DO UPDATE SET
        has_production_data  = EXCLUDED.has_production_data,
        has_inspection_data  = EXCLUDED.has_inspection_data,
        has_shipping_data    = EXCLUDED.has_shipping_data,
        overall_completeness = EXCLUDED.overall_completeness,
        last_evaluated_at    = EXCLUDED.last_evaluated_at;

    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_production_completeness
    AFTER INSERT OR UPDATE OR DELETE ON ops.production_records
    FOR EACH ROW EXECUTE FUNCTION ops.fn_refresh_data_completeness();

CREATE TRIGGER trg_inspection_completeness
    AFTER INSERT OR UPDATE OR DELETE ON ops.inspection_records
    FOR EACH ROW EXECUTE FUNCTION ops.fn_refresh_data_completeness();

CREATE TRIGGER trg_shipping_completeness
    AFTER INSERT OR UPDATE OR DELETE ON ops.shipping_records
    FOR EACH ROW EXECUTE FUNCTION ops.fn_refresh_data_completeness();


-- ---------------------------------------------------------------------------
-- 10. VIEWS
-- ---------------------------------------------------------------------------

-- 10a. Cross-functional lot summary (AC1, AC2, AC3, AC7, AC8)
--      Single query replaces opening three separate spreadsheets.
--      Filter by lot_code for lot lookup, or start_date / end_date for
--      date-range analysis (AC3).
CREATE OR REPLACE VIEW ops.v_lot_summary AS
SELECT
    l.lot_id,
    l.lot_code,
    l.start_date,
    l.end_date,

    -- Production summary
    dc.has_production_data,
    COUNT(DISTINCT pr.production_id)                        AS production_run_count,
    SUM(pr.quantity_produced)                               AS total_units_produced,
    SUM(pr.units_planned)                                   AS total_units_planned,
    ROUND(
        100.0 * SUM(pr.quantity_produced) /
        NULLIF(SUM(pr.units_planned), 0), 1
    )                                                       AS attainment_pct,
    SUM(pr.downtime_min)                                    AS total_downtime_min,
    BOOL_OR(pr.line_issue)                                  AS any_line_issue,
    COUNT(DISTINCT pr.production_id)
        FILTER (WHERE pr.line_issue = TRUE)                 AS production_issue_count,

    -- Inspection summary
    dc.has_inspection_data,
    COUNT(DISTINCT ir.inspection_id)                        AS inspection_count,
    BOOL_OR(ir.issue_flag)                                  AS any_inspection_issue,
    COUNT(DISTINCT ir.inspection_id)
        FILTER (WHERE ir.issue_flag = TRUE)                 AS inspection_issue_count,

    -- Shipping summary
    dc.has_shipping_data,
    COUNT(DISTINCT sr.shipping_id)                          AS shipment_count,
    SUM(sr.qty_shipped)                                     AS total_qty_shipped,
    ARRAY_AGG(DISTINCT sr.shipment_status::TEXT)
        FILTER (WHERE sr.shipment_status IS NOT NULL)       AS shipment_statuses,
    BOOL_OR(sr.shipment_status IN ('On Hold', 'Backordered'))
                                                            AS any_shipment_blocked,

    -- Data completeness
    dc.overall_completeness,
    dc.last_evaluated_at                                    AS completeness_last_updated

FROM ops.lots                       l
LEFT JOIN ops.data_completeness     dc ON dc.lot_id = l.lot_id
LEFT JOIN ops.production_records    pr ON pr.lot_id = l.lot_id
LEFT JOIN ops.inspection_records    ir ON ir.lot_id = l.lot_id
LEFT JOIN ops.shipping_records      sr ON sr.lot_id = l.lot_id
GROUP BY
    l.lot_id, l.lot_code, l.start_date, l.end_date,
    dc.has_production_data, dc.has_inspection_data, dc.has_shipping_data,
    dc.overall_completeness, dc.last_evaluated_at;

COMMENT ON VIEW ops.v_lot_summary IS
    'Cross-functional lot summary (AC1, AC2, AC7, AC8). Filter by lot_code or start_date/end_date for date-range analysis (AC3). Replaces opening three separate spreadsheets.';


-- 10b. Lots with inspection issues and their shipping status (AC5, AC6)
--      Answers: "Have lots with inspection issues already shipped?"
CREATE OR REPLACE VIEW ops.v_inspection_issue_shipping AS
SELECT
    l.lot_id,
    l.lot_code,
    l.start_date,
    ir.inspection_date,
    ir.inspection_result,
    ir.inspector_notes,
    sr.ship_date,
    sr.shipment_status,
    sr.hold_reason,
    sr.customer,
    sr.destination,
    dc.overall_completeness
FROM ops.lots                       l
JOIN  ops.inspection_records        ir ON ir.lot_id = l.lot_id
                                      AND ir.issue_flag = TRUE
LEFT JOIN ops.shipping_records      sr ON sr.lot_id   = l.lot_id
LEFT JOIN ops.data_completeness     dc ON dc.lot_id   = l.lot_id;

COMMENT ON VIEW ops.v_inspection_issue_shipping IS
    'All lots with at least one inspection issue, joined to their shipping status. Answers AC6: have lots with inspection issues shipped?';


-- 10c. Incomplete lots — missing data from one or more functions (AC4, AC10)
--      Every new lot appears here immediately (score = 0) because the init
--      trigger pre-populates data_completeness on lot creation.
CREATE OR REPLACE VIEW ops.v_incomplete_lots AS
SELECT
    l.lot_id,
    l.lot_code,
    l.start_date,
    l.end_date,
    dc.has_production_data,
    dc.has_inspection_data,
    dc.has_shipping_data,
    dc.overall_completeness,
    dc.last_evaluated_at,
    CASE
        WHEN NOT dc.has_production_data
         AND NOT dc.has_inspection_data
         AND NOT dc.has_shipping_data   THEN 'No data in any function'
        WHEN NOT dc.has_production_data
         AND NOT dc.has_inspection_data THEN 'Missing production and inspection'
        WHEN NOT dc.has_production_data
         AND NOT dc.has_shipping_data   THEN 'Missing production and shipping'
        WHEN NOT dc.has_inspection_data
         AND NOT dc.has_shipping_data   THEN 'Missing inspection and shipping'
        WHEN NOT dc.has_production_data THEN 'Missing production data'
        WHEN NOT dc.has_inspection_data THEN 'Missing inspection data'
        WHEN NOT dc.has_shipping_data   THEN 'Missing shipping data'
        ELSE 'Complete'
    END AS completeness_note
FROM ops.lots               l
JOIN ops.data_completeness  dc ON dc.lot_id = l.lot_id
WHERE dc.overall_completeness < 100;

COMMENT ON VIEW ops.v_incomplete_lots IS
    'Lots with overall_completeness < 100. Every new lot appears here immediately (score starts at 0). Surfaces data gaps with plain-English notes (AC4, AC10).';


-- 10d. Issue counts by production line (AC5)
--      Answers: "Which production lines had the most issues and what kind?"
CREATE OR REPLACE VIEW ops.v_issues_by_production_line AS
SELECT
    pr.production_line,
    COUNT(*)                                                        AS total_runs,
    COUNT(*) FILTER (WHERE pr.line_issue = TRUE)                    AS issue_runs,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE pr.line_issue = TRUE) /
        NULLIF(COUNT(*), 0), 1
    )                                                               AS issue_rate_pct,
    COUNT(*) FILTER (WHERE pr.primary_issue = 'Tool wear')          AS tool_wear_count,
    COUNT(*) FILTER (WHERE pr.primary_issue = 'Sensor fault')       AS sensor_fault_count,
    COUNT(*) FILTER (WHERE pr.primary_issue = 'Material shortage')  AS material_shortage_count,
    COUNT(*) FILTER (WHERE pr.primary_issue = 'Changeover delay')   AS changeover_delay_count,
    COUNT(*) FILTER (WHERE pr.primary_issue = 'Quality hold')       AS quality_hold_count,
    COUNT(*) FILTER (WHERE pr.primary_issue = 'Operator training')  AS operator_training_count
FROM ops.production_records pr
GROUP BY pr.production_line
ORDER BY issue_runs DESC;

COMMENT ON VIEW ops.v_issues_by_production_line IS
    'Issue count and rate by production line with breakdown by issue type. Answers AC5: which lines had the most issues?';


-- ---------------------------------------------------------------------------
-- END OF DDL
-- ---------------------------------------------------------------------------
