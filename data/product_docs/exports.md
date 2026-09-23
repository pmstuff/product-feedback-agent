# Prism Exports — Feature Documentation

**Version:** 3.4  
**Last updated:** 2026-02-15

---

## Overview

Prism supports exporting report data and dashboard views for offline analysis,
sharing with stakeholders, and archiving. All exports are triggered manually
from the Prism UI.

---

## Supported export types

### 1. CSV data export

- **Where:** Report view → Export button → Download CSV
- **Row limit:** 10,000 rows per file. If your report returns more rows, you
  will receive the first 10,000 only. There is no pagination or split-file option.
- **Encoding:** UTF-8
- **Available on:** Growth, Professional, Enterprise plans
- **Known issues:**
  - Exports > 5,000 rows may fail intermittently under high server load (P2 bug,
    tracked in ENG-4821; no fix date confirmed)
  - Export generation times above ~3,000 rows can be slow (5–15 minutes) during
    peak hours (09:00–11:00 UTC)

### 2. PDF dashboard export

- **Where:** Dashboard view → Share → Export as PDF
- **Content:** Entire dashboard as a single PDF (one page per chart row)
- **Branding:** Prism logo and colour scheme only. Custom branding (logo, colours,
  fonts) is **not supported**
- **Available on:** Growth, Professional, Enterprise plans

---

## What is NOT supported

The following export capabilities are **not currently available** in Prism 3.4:

| Capability | Status | Notes |
|------------|--------|-------|
| Excel (.xlsx) export | ❌ Not available | Frequently requested; in scoping for a future release |
| Scheduled / automated exports | ❌ Not available | Must be triggered manually each time |
| Export to cloud storage (S3, GCS, Azure Blob) | ❌ Not available | No programmatic export path exists |
| Export API (REST or webhook) | ❌ Not available | Export is UI-only; no API endpoint |
| Bulk export (> 10,000 rows) | ❌ Not available | 10k row cap is a hard limit in the current architecture |
| Custom-branded PDF | ❌ Not available | All PDFs use Prism default branding |
| Parquet / Arrow export | ❌ Not available | No plans to add columnar formats |
| Email delivery of exports | ❌ Not available | In design for a future release |

---

## Workarounds recommended to customers

**For Excel:** Export CSV → open in Excel → Save As .xlsx. This is a manual step
but preserves all data. Formatting (formulas, pivot tables) must be rebuilt manually.

**For row limits:** Run multiple filtered exports with different date ranges or
segment filters and concatenate the files. This is cumbersome and error-prone.

**For scheduled exports:** Use the Prism REST API ingest webhook to pull data into
an intermediate system (e.g. a cron job on your server), then use your own tooling
to write it to CSV or your data warehouse.

---

## Performance guidance

- Exports > 3,000 rows should be scheduled outside peak hours when possible
- If an export fails, wait 5 minutes and retry before raising a support ticket
- Large PDF exports (dashboards with > 20 charts) may time out on the Professional
  plan; Enterprise customers have higher timeout limits

---

## Roadmap signal (internal only)

- **Excel export:** Scoping phase. Likely requires third-party library integration.
  Target: Q3 2026 at the earliest. Not publicly committed.
- **Scheduled email export:** In design. Target: Q4 2026.
- **Cloud storage push (S3):** Backlog. No timeline.
- **Export API:** No current plans. Re-evaluate after the Export 2.0 milestone.
