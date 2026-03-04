# Tech Stack Decision Record: Operations Unification Tool

## Status
Proposed

## Context
Our architecture is a **modular monolith** with a layered backend and a single relational database, focused on joining and querying thousands to millions of rows of Production, Inspection, and Shipping data. The team is small (1–2 developers), so the stack must optimize for developer productivity, strong data processing capabilities, and straightforward deployment. We also want a good path toward future AI-assisted insights over operational data, along with strong community support and ecosystem maturity. The decision is evaluated along five dimensions: (1) AI support strength, (2) popularity & community answers, (3) ecosystem maturity, (4) deployment simplicity, and (5) path to the next architecture.

## Decision
Adopt the **FastAPI + React + PostgreSQL** stack, managed with **Poetry**.

- **Backend:** FastAPI (Python) for a high-performance, async-friendly REST API.
- **Frontend:** React (with Vite) using Tailwind CSS for a responsive, factory-floor-friendly UI.
- **Database:** PostgreSQL for robust relational joins, indexing, and scalability.
- **Package Management:** Poetry for deterministic Python dependency management and environment isolation.
- **Data Access:** SQLAlchemy (ORM) with clear separation between entities and business logic.
- **Containerization:** Docker and Docker Compose for consistent local and production environments.

### Tech Stack Dimensions

| Dimension                         | Rating  | Rationale |
| :---                             | :---    | :--- |
| **1) AI Support Strength**       | High    | Python is the de facto standard for AI/ML; future anomaly detection or forecasting can be added without changing stack. |
| **2) Popularity & Community**    | High    | React and FastAPI both have large communities, tutorials, and Q&A coverage, reducing time spent unblocking issues. |
| **3) Ecosystem Maturity**        | High    | PostgreSQL and Python data libraries (Pandas/Polars) are mature and well-suited for spreadsheet ingestion and heavy joins. |
| **4) Deployment Simplicity**     | High    | A small set of containers (frontend, backend, DB) can be deployed on a single VM or internal server using Docker Compose. |
| **5) Path to Next Architecture** | Clear   | FastAPI’s modular routers and domain boundaries support later extraction into separate services if needed. |

## Alternatives Considered

1. **Streamlit + Poetry**
   - **Pros:** Very fast to prototype; ideal for quick internal dashboards or proofs of concept.
   - **Cons:** UI tightly coupled to Python execution, re-running scripts on interaction; less suitable for multi-user, meeting-critical queries over millions of rows and more limited in fine-grained UI/UX control.

2. **Next.js + Prisma + PostgreSQL (Full-Stack TypeScript)**
   - **Pros:** Single language (TypeScript) across frontend and backend; strong type safety; good web ecosystem.
   - **Cons:** Less ergonomic for heavy data wrangling and spreadsheet-based ETL compared to Python; would require additional data tooling or services for complex production/inspection/shipping analytics.

3. **.NET Core + SQL Server + Angular**
   - **Pros:** Enterprise-grade stack, common in manufacturing; strong tooling and long-term support.
   - **Cons:** More boilerplate and ceremony for a 1–2 person team; slower to iterate compared to FastAPI/Python for data-heavy workflows.

## Consequences

### Positive
- **High productivity:** FastAPI’s concise model and automatic OpenAPI/Swagger generation reduce boilerplate and make backend–frontend integration faster.
- **Data strength:** PostgreSQL plus SQLAlchemy and Python data libraries provide strong support for large joins, complex filters, and spreadsheet ingestion at scale, helping to meet “Meeting-Ready” performance requirements.
- **Determinism & reliability:** Poetry’s lockfile ensures consistent environments across machines and servers, decreasing “works on my machine” issues.
- **Future AI readiness:** Python backend makes it straightforward to introduce AI-based features such as anomaly detection, forecasting, or natural-language querying over operations data.

### Negative
- **Context switching:** Developers need to be comfortable in both TypeScript (frontend) and Python (backend), which can increase cognitive load.
- **Initial setup complexity:** Setting up Docker, Poetry, React/Vite, and Tailwind is slightly more involved than a simpler, single-process stack.
- **Async considerations:** To fully benefit from FastAPI’s async model, care is needed in choosing async-compatible drivers and avoiding blocking I/O during large database operations.
