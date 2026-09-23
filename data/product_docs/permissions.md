# Prism Permissions and Roles — Feature Documentation

**Version:** 3.4  
**Last updated:** 2026-01-20

---

## Overview

Prism uses a role-based access control (RBAC) model with three fixed roles.
Permissions are applied at the **workspace level** — there is currently no
way to restrict access at the dashboard, folder, or row level.

---

## Roles

### Admin
- Full access to all dashboards, reports, and data sources
- Can invite and remove users
- Can change user roles
- Can access billing and plan settings
- Can view the audit log

### Editor
- Can create, edit, and delete dashboards and reports
- Can connect new data sources
- Can share dashboards via public or password-protected links
- Cannot manage users or access billing
- Can apply and save filters on dashboards

### Viewer
- Can view dashboards and reports they have been explicitly shared with
- **Cannot** apply or save filters (filters must be pre-set by an Editor or Admin)
- **Cannot** export data (CSV or PDF export is not available to Viewer role)
- **Cannot** create or edit any content
- **Cannot** connect data sources

> **Note:** The Viewer export restriction is intentional for data governance reasons.
> Some Enterprise customers have requested Viewer-level exports; this is under
> evaluation.

---

## What is NOT supported

| Capability | Status | Notes |
|------------|--------|-------|
| Custom roles | ❌ Not available | Only Admin, Editor, Viewer exist |
| Dashboard-level permissions | ❌ Not available | All roles apply workspace-wide |
| Row-level security (RLS) | ❌ Not available | All users see all rows in a dataset |
| Department / team grouping | ❌ Not available | No concept of teams or groups inside a workspace |
| External / guest access | ❌ Not available | External users must be given a full Viewer seat |
| Time-limited access | ❌ Not available | Invitations do not expire |
| Viewer-level filtering | ❌ Not available | Known limitation; frequently requested |
| Viewer-level exports | ❌ Not available | Under evaluation for a future release |

---

## SSO / Identity

- **Email + password:** Available on all plans
- **SAML 2.0 SSO:** In **closed beta** — available to Enterprise customers only.
  Must be manually enabled by the Prism support team. Okta, Azure AD, and Google
  Workspace identity providers are confirmed working. Others may work but are
  untested.
- **SCIM provisioning:** Not available. User provisioning must be done manually
  in the Prism UI even when SSO is enabled.
- **MFA:** Available for email/password accounts (TOTP via authenticator app)

---

## Audit log

The Prism audit log records the following events:

| Event | Logged? |
|-------|---------|
| User login | ✅ Yes |
| User invitation | ✅ Yes |
| User role change | ✅ Yes |
| Dashboard view | ❌ No |
| Data export | ❌ No |
| Dashboard edit / creation | ❌ No |
| Data source connection | ❌ No |

> **Compliance note:** The current audit log does **not** meet SOC 2 Type II
> or GDPR Article 30 requirements for data-access logging. Enterprise customers
> with compliance requirements should be made aware of this limitation.

---

## Roadmap signal (internal only)

- **Custom roles:** Backlog. No timeline confirmed. High-complexity item.
- **Row-level security:** Blocked on custom roles shipping first.
- **SSO GA (self-serve):** Target Q3 2026. Currently requires manual enablement.
- **SCIM provisioning:** Backlog. No timeline.
- **Viewer filtering:** In design. Likely Q3 2026.
- **Audit log expansion (data access + exports):** Backlog. Priority increasing
  due to Enterprise compliance pressure.
- **Guest / external access:** No current plans.
