# Prism Integrations — Feature Documentation

**Version:** 3.4  
**Last updated:** 2026-02-28

---

## Overview

Prism connects to data sources and third-party tools via native connectors,
a REST ingest API, and an outbound webhook system. The integrations catalogue
is limited compared to dedicated ETL/ELT tools; Prism focuses on being a
best-in-class analytics layer, not a data pipeline.

---

## Native data source connectors (GA)

| Connector | Type | Notes |
|-----------|------|-------|
| PostgreSQL | Direct query | SSL required |
| MySQL 5.7+ | Direct query | SSL required |
| Amazon Redshift | Direct query | IAM or password auth |
| Google BigQuery | Direct query | Service account JSON |
| Snowflake | Direct query | Key-pair or password auth |
| CSV file upload | Batch ingest | Up to 500 MB per file |
| JSON file upload | Batch ingest | Flat or nested (1 level) |

---

## Native application integrations

### Slack (closed beta)
- **Status:** Closed beta — available to Enterprise customers on request
- **Capability:** Send threshold-based alerts to a Slack channel when a metric
  crosses a defined value (e.g. "DAU drops below 1,000 → notify #data-alerts")
- **Limitations:**
  - One Slack workspace per Prism workspace
  - Alert-only — no bidirectional sync or Slash commands
  - Cannot query Prism from Slack

### Google Analytics (GA)
- **Status:** Generally available
- **Capability:** Pull session, event, and conversion data from GA4 properties
  into Prism dashboards
- **Limitations:** Read-only; historical data only (no real-time stream)

---

## API and webhook integrations

### Ingest API
- **Status:** Available on Professional and Enterprise plans
- **Capability:** Push data into Prism from any system via a REST endpoint
- **Documentation:** Available in the developer portal
- **Rate limit:** 10 requests/second; 1 GB/day

### Outbound webhook (data export)
- **Status:** Not available
- **Capability:** ❌ Prism cannot push data OUT via webhook automatically.
  The ingest API is inbound only. Programmatic data export does not exist.

---

## What is NOT supported

| Integration | Status | Notes |
|-------------|--------|-------|
| Salesforce | ❌ Not available | Partnership discussions ongoing; no timeline |
| HubSpot | ❌ Not available | Under evaluation by partnerships team |
| Zapier | ❌ Not available | No current plans; re-evaluate after Slack ships |
| Make (Integromat) | ❌ Not available | No current plans |
| Google Sheets live sync | ❌ Not available | One-way CSV export is the only option |
| Notion | ❌ Not available | No current plans |
| Jira | ❌ Not available | No current plans |
| Microsoft Teams | ❌ Not available | Requested; backlog, no timeline |
| dbt Cloud | ❌ Not available | Integration with dbt is manual (connect to underlying DB) |
| Fivetran / Airbyte | ❌ Not available | Use the Ingest API as an alternative |
| REST export API | ❌ Not available | Export is UI-only |

---

## Frequently requested integrations (ranked by volume)

Based on support tickets and sales calls (2025 H2):

1. **Salesforce** — 34 customers requesting; primary use case: sync opportunity and
   account data for revenue analytics dashboards
2. **HubSpot** — 21 customers requesting; primary use case: customer health metrics
   and marketing funnel analysis
3. **Zapier** — 18 customers requesting; primary use case: trigger external workflows
   when Prism metrics cross thresholds
4. **Google Sheets** — 16 customers requesting; primary use case: keep a live
   Sheets tab in sync with a Prism report (replaces manual CSV export)
5. **Slack** (beyond alerts) — 12 customers requesting query-in-Slack capability
6. **Microsoft Teams** — 9 customers requesting; primarily Enterprise segment

---

## Roadmap signal (internal only)

- **Slack beta → GA:** Target Q2 2026. Pending stability validation on 10 beta
  accounts.
- **Salesforce connector:** Partnership discussions in progress. Engineering scoping
  not started. No committed timeline.
- **HubSpot connector:** Under evaluation. No engineering work started.
- **Zapier integration:** No current plans. Will re-evaluate after Slack ships GA.
- **Google Sheets sync:** No current plans. The manual CSV workaround is considered
  sufficient for now.
- **Export API:** No current plans. This would unlock many programmatic use cases
  (including Zapier-style automation) but is a large engineering investment.
