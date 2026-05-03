# ADR-0005 — Streamlit + Superset for the Visualization Layer

**Date:** 2026-01-15
**Status:** Accepted

## Context

The platform needs two types of visualization: (1) a KPI summary view with near-real-time data refresh and an AI chat interface for natural-language queries, and (2) an interactive BI layer where analysts can filter, drill down, and build ad-hoc charts without writing code. A single tool would either over-engineer the KPI view or under-deliver on BI flexibility.

## Decision

Use **two complementary tools**:

- **Streamlit** for the operational KPI dashboard (`dashboard/app.py`) — shows pipeline health metrics, stale opportunity alerts, PDF export, and a chat interface backed by the Gemini/OpenAI API.
- **Apache Superset** for the interactive BI dashboard — provides a full chart library (funnel, bar, pie, table) with filter controls, linked directly from the Streamlit app via a `st.link_button`.

Both tools read from the same BigQuery gold-layer tables (`layer_gold.*`).

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Streamlit** (KPI layer) | Pure Python, fast to build, supports custom components and LLM chat | Not designed for ad-hoc BI; adding many charts increases code complexity |
| **Superset** (BI layer) | No-code chart builder, SQL editor, role-based access, REST API | Cannot embed Python logic or LLM features natively |
| **Grafana** | Excellent for time-series monitoring | Weak support for CRM/dimensional data; chart types limited for business KPIs |
| **Metabase** | Easy to use | Limited API; fewer chart types than Superset; embedding requires paid tier |
| **Dash (Plotly)** | Full Python control, highly customizable | More boilerplate than Streamlit; no built-in BI chart builder |
| **Tableau / Power BI** | Best-in-class BI | Commercial licenses; not suitable for a self-hosted student project |

## Rationale

The two-tool approach mirrors common production architectures where a lightweight ops dashboard co-exists with a deeper BI layer. Streamlit handles the Python-heavy requirements (AI chat, PDF generation with fpdf2, custom KPI styling) that BI tools cannot do without plugins. Superset handles the flexible drill-down requirements that would require hundreds of lines of Plotly code in Streamlit. Linking them via a single button keeps the UX simple while delivering the full feature set.

## Consequences

- **Positive:** Each tool does what it is best at; the Streamlit app stays lean (KPIs + actions only); Superset's SQL Lab allows analysts to run ad-hoc queries directly against BigQuery.
- **Negative:** Two services to maintain and keep running; Superset requires Docker Compose with PostgreSQL and Redis, adding ~500 MB RAM overhead. Auto-refresh in Streamlit relies on `@st.cache_data(ttl=60)` rather than a true push mechanism — the data is stale until the user re-triggers a page interaction.
