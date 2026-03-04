## lots
- lot_id (Primary Key)
- lot_code (Unique)
- start_date
- end_date (Optional — NULL while lot is still open)

## production_records
- production_id (Primary Key)
- lot_id (Foreign Key)
- production_date
- production_line
- quantity_produced
- shift
- part_number
- units_planned
- downtime_min (Default 0)
- line_issue (Boolean)
- primary_issue (Optional — only set when line_issue is true)
- supervisor_notes (Optional)

## inspection_records
- inspection_id (Primary Key)
- lot_id (Foreign Key)
- inspection_date
- inspection_result
- issue_flag (Boolean)
- inspector_notes (Optional)

## shipping_records
- shipping_id (Primary Key)
- lot_id (Foreign Key)
- ship_date
- shipment_status
- destination
- customer
- sales_order (Optional)
- carrier (Optional — NULL for customer pickup)
- bol_number (Optional, Unique)
- tracking_pro (Optional)
- qty_shipped (Default 0)
- hold_reason (Optional — required when shipment is On Hold)
- shipping_notes (Optional)

## data_completeness
- lot_id (Primary Key / Foreign Key)
- has_production_data (Boolean)
- has_inspection_data (Boolean)
- has_shipping_data (Boolean)
- overall_completeness (Integer percentage: 0, 33, 67, or 100)
- last_evaluated_at

## Relationships
- One lots can have many production_records.
- One lots can have many inspection_records.
- One lots can have many shipping_records.
- One lots has one data_completeness.

---

## ERD

```mermaid
erDiagram
    lots ||--o{ production_records : tracks
    lots ||--o{ inspection_records : verified_by
    lots ||--o{ shipping_records : delivered_via
    lots ||--|| data_completeness : audit_summary

    lots {
        int     lot_id      PK
        string  lot_code    UK
        date    start_date
        date    end_date
    }

    production_records {
        int     production_id   PK
        int     lot_id          FK
        date    production_date
        string  production_line
        int     quantity_produced
        string  shift
        string  part_number
        int     units_planned
        int     downtime_min
        boolean line_issue
        string  primary_issue
        string  supervisor_notes
    }

    inspection_records {
        int     inspection_id   PK
        int     lot_id          FK
        date    inspection_date
        string  inspection_result
        boolean issue_flag
        string  inspector_notes
    }

    shipping_records {
        int     shipping_id     PK
        int     lot_id          FK
        date    ship_date
        string  shipment_status
        string  destination
        string  customer
        string  sales_order
        string  carrier
        string  bol_number      UK
        string  tracking_pro
        int     qty_shipped
        string  hold_reason
        string  shipping_notes
    }

    data_completeness {
        int      lot_id                PK "FK"
        boolean  has_production_data
        boolean  has_inspection_data
        boolean  has_shipping_data
        int      overall_completeness
        datetime last_evaluated_at
    }
```
