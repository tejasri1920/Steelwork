# Project Scope & Assumptions: Operations Data Unification

## 1. Project Scope
This section defines the boundaries of the implementation to ensure all Acceptance Criteria (AC) are met and to prevent **Scope Creep**.

### **In-Scope (Delivered Features)**
* **Data Aggregation:** A unified reporting interface that joins records from three sources: Production, Inspection, and Shipping (AC1).
* **Relational Logic:** Implementation of a join logic to ensure records align strictly by **Lot ID** across all functions (AC2).
* **Filtering System:** Capability to query the unified dataset by **Lot ID** or a specific **Date Range** (AC3).
* **Visual Indicators:** Explicit UI labels (e.g., "Data Missing" or "N/A") for lots where information is incomplete in one or more source files (AC4, AC10).
* **Operational Summaries:** * Grouping logic to identify production lines with the highest frequency of inspection issues (AC5).
    * Status mapping to confirm if lots with inspection failures have been shipped (AC6).
* **Consolidated View:** A "Meeting-Ready" dashboard designed to replace the manual opening of multiple spreadsheets (AC7, AC8).

### **Out-of-Scope (Excluded Features)**
* **CRUD Operations:** The tool is Read-Only; it will not support creating, updating, or deleting source records.
* **Source Data Cleaning:** Automated fixing of typos, duplicate entries, or inconsistent Lot ID formats within the original spreadsheets.
* **Automated Alerts:** Push notifications or email triggers for inspection failures.
* **Write-Back Functionality:** Data will not be pushed back into the source spreadsheets or ERP systems.

---

## 2. Engineering Assumptions
These assumptions define the technical baseline and protect the developer from "This is not what I wanted" claims.

* **A1: Key Consistency:** The **Lot ID** is a unique, standardized string used across all source spreadsheets (e.g., no variations like "Lot-101" vs "101").
* **A2: Source Data Access:** All source files (Production, Inspection, Shipping) are stored in a centralized, accessible location with consistent file names.
* **A3: Header Stability:** Column headers for "Lot ID," "Date," and "Production Line" will remain unchanged in the source files.
* **A4: Issue Definition:** An "inspection issue" is defined by a pre-existing status column (e.g., "Fail" or "Rejected") within the Inspection data.
* **A5: Data Refresh:** Data is assumed to be updated on a [Batch/Daily] basis; real-time "live" streaming is not required.
* **A6: Deterministic Results:** The same query will always return the same result unless the underlying source data has changed (AC9).

---

