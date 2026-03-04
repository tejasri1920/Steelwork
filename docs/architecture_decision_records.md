# Title
Architecture Decision Record (ADR): Operations Unification Tool

## Status
Proposed

## Context
An operations analyst needs to unify Production, Inspection, and Shipping data that currently live in separate spreadsheets. The tool must allow querying by Lot ID or date range and present aligned records from all functions in a single, meeting-ready view, fulfilling the acceptance criteria around data alignment, visibility of missing data, and consistent results over time (AC1–AC4, AC7–AC10). The team is small (1–2 experienced developers), the expected usage is department-wide with a few concurrent users, data volume may reach thousands to millions of rows, and the timeline is weeks to a few months, which constrains architectural complexity and operational overhead.

## Decision
Adopt a modular monolithic, client–server web application with a layered backend, a single relational database, and synchronous request–response interaction.

- System roles & communication: Client–server, with a web frontend (e.g., browser-based UI) consuming a backend API.
- Deployment & evolution: Single deployable monolith, structured into clear modules (production, inspection, shipping, reporting).
- Code organization: Layered architecture separating Presentation, Business Logic, and Data Access.
- Data & state ownership: Single centralized relational database (e.g., PostgreSQL/SQL Server) holding normalized Production, Inspection, and Shipping tables.
- Interaction model: Synchronous requests where the client waits for responses to Lot ID or date range queries.

## Alternatives Considered

1. **Event-driven architecture with asynchronous processing**
   - Use events (e.g., “inspection_updated”, “shipment_created”) and background consumers to build views.
   - Rejected because it adds significant operational and conceptual complexity for a small team, while the primary use case is interactive, request–response querying in meetings.

2. **Microservices with database-per-service**
   - Separate services for Production, Inspection, and Shipping, each owning its own database, with aggregation done via APIs or a reporting service.
   - Rejected because the team size and timeline do not justify distributed deployment, cross-service coordination, and complex data consistency strategies for this internal reporting-style tool.

3. **Spreadsheet-only or desktop-based solution**
   - Use macros, Power Query, or a desktop BI/reporting tool directly on spreadsheets.
   - Rejected because it offers weaker control over role-based access, maintainability, and repeatable, consistent query behavior at higher data volumes.

## Consequences

### Positive
- Strong consistency: A single relational database and synchronous access provide deterministic, repeatable results when reviewing the same lot or date range, aligning with the need for consistent answers in meetings.
- Delivery velocity: A modular monolith with a layered backend allows 1–2 developers to implement ingestion, alignment, and UI within weeks, minimizing deployment and operational overhead.
- Maintainability: Changes to spreadsheet formats or locations are isolated to the Data Access layer, while business logic and UI remain stable.
- Evolution path: Clear domain modules (production, inspection, shipping, reporting) keep open the option of later extracting components if scaling or organizational needs change.

### Negative
- Scalability and performance limits: As data grows toward millions of rows and query complexity increases, the single database and synchronous model may require careful indexing, query tuning, and vertical scaling to maintain acceptable response times.
- Single-point-of-failure risk: The monolithic application and single database instance create availability dependencies; outages affect all users until backup, monitoring, and recovery procedures are in place.
- Limited decoupling: Tight coupling through a single schema means cross-cutting changes (e.g., major schema redesign) can impact multiple modules simultaneously, requiring coordinated deployments.
