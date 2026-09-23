# Prism Analytics — Product Overview

**Version:** 3.4  
**Last updated:** 2026-03-01  
**Audience:** Internal product team and customer-facing staff

---

## What is Prism?

Prism is a cloud-based business intelligence and analytics platform for B2B SaaS
companies. It allows teams to connect their data sources, build dashboards and
reports, and share insights across the organisation.

Prism is designed for data teams and business analysts who need to move faster
than a traditional BI tool allows, without the infrastructure overhead of a
self-hosted solution.

---

## Current capabilities (GA)

### Data connectivity
- **Direct connectors:** PostgreSQL, MySQL, Redshift, BigQuery, Snowflake
- **File upload:** CSV (up to 500 MB), JSON
- **REST API ingest:** custom HTTP endpoints can push data into Prism via webhook

### Dashboards and visualisation
- Drag-and-drop chart builder (bar, line, pie, scatter, table, funnel)
- Up to 50 charts per dashboard
- Dashboard-level filters shared across all charts
- Real-time refresh (configurable from 1 min to 24 hrs)

### Exports
- CSV export (up to 10,000 rows per file)
- PDF export of a single dashboard (Prism-branded; custom branding not available)
- Manual export only — no scheduled or automated exports

### User management
- Three fixed roles: **Admin**, **Editor**, **Viewer**
- Workspace-level permissions only
- Email/password authentication
- SSO via SAML 2.0 (currently in **closed beta** — available to Enterprise customers on request)
- Audit log: login events and user invitations only

### Collaboration
- Dashboard comments and @mentions
- Shareable view-only links (password-protected, 7-day expiry)

---

## Known limitations and gaps

| Area | Current state | Gap |
|------|--------------|-----|
| Export row limit | 10,000 rows | Large datasets require multiple manual exports |
| Export formats | CSV, PDF | No Excel (.xlsx), no Parquet, no direct-to-cloud |
| Scheduled exports | Not available | Manual only |
| Custom roles | Not available | Three fixed roles; no department or row-level permissions |
| Row-level security | Not available | All users with dashboard access see all rows |
| Guest / external access | Not available | External collaborators must be given a full Viewer seat |
| SSO | Closed beta | Not self-serve; requires Enterprise plan and manual enablement |
| Integrations | Limited | No native CRM, messaging, or workflow-automation integrations |
| Audit log completeness | Partial | Login and invite events only; no data-access or export events |
| Onboarding | Self-serve docs only | No guided setup wizard, no in-product checklist, no demo workspace |

---

## Pricing tiers

| Tier | Users | Key differences |
|------|-------|----------------|
| Starter | Up to 5 | 3 dashboards, CSV export only |
| Growth (SMB) | Up to 25 | Unlimited dashboards, PDF export |
| Professional (Mid-market) | Up to 100 | Priority support, API access |
| Enterprise | Unlimited | SSO (beta), dedicated CSM, custom SLA |

---

## Planned roadmap (next 2 quarters)

The following items are on the internal roadmap but have **not** been publicly
committed. Do not share specific timelines with customers.

- Excel (.xlsx) export — in scoping
- Scheduled export to email — in design
- Slack integration for threshold alerts — engineering in progress
- Custom role builder — backlog, no timeline
- Demo / sandbox workspace for onboarding — backlog

---

## What is not planned

The following have been deliberately deferred or deprioritised:

- Row-level security — deferred until custom roles ship
- Zapier integration — no current plans; evaluate after Slack ships
- HubSpot native connector — under evaluation by partnerships team
- Salesforce native connector — partnership discussions ongoing, no timeline
- Google Sheets live sync — no current plans
- Export API (bulk, programmatic) — no current plans
