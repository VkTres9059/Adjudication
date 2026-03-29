# FletchFlow — Claims Adjudication System PRD

## Original Problem Statement
Build a scalable, API-first claims adjudication system supporting multiple lines of coverage. Start with Medical coverage, use Microsoft MFA for authentication, accept EDI 834/837 input with 835 output. Provide reporting for claims/eligibility. Implement strict duplicate claim prevention, built-in Medicare fee schedules, multi-line coverage, a comprehensive Preventive Coverage module, and Group Management.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI, collapsible categorized sidebar
- **Backend**: FastAPI (modular routers), MongoDB, JWT Auth (MSAL fallback)
- **Structure**: `/app/backend/routers/`, `/app/backend/services/`, `/app/backend/models/`, `/app/backend/core/`

## Completed Features (as of Mar 2026)

### Phase 1 — Core Claims Engine
- Multi-line claims adjudication (Medical, Dental, Vision, Pharmacy)
- Medicare fee schedule pricing (377+ CPT codes, 87 GPCI localities)
- Real-time duplicate claim detection
- EDI 834/837 intake, 835 output (mocked parser)
- JWT authentication with role-based access (Admin, Examiner, Viewer)
- Group Management with stop-loss analytics
- Preventive Coverage module
- Dashboard with metrics, claims-by-status, claims-by-type charts

### Phase 2 — Adjudication Gateway & Examiner Workspace
- Tiered Authorization Matrix (auto-approve, examiner review, manager approval)
- Global Adjudication Gateway settings
- Examiner Queue Dashboard with auto-assignment engine
- Hard Hold / Soft Hold claim states
- Prior Authorization tracking
- COB (Coordination of Benefits) processing

### Phase 3 — Eligibility & Member Lifecycle
- Reconciliation Dashboard
- Retroactive Termination / Clawback
- Pending Eligibility Queue
- Age-Out Rules

### Phase 4 — Backend Refactoring
- Migrated ~3,850 line server.py monolith to modular router architecture
- 16 routers: auth, plans, members, groups, claims, examiner, duplicates, dashboard, reports, edi, codes, network, prior_auth, preventive, settings, audit, hour_bank

### Phase 5 — Navigation & UX
- Collapsible categorized sidebar (Operations, Plan Management, Claims Center, Network & Groups)

### Phase 6 — Variable Hour Bank Module (Base + Upgrade)
- **Base**: SFTP work report ingestion, hour bank ledger, auto-status flip
- **Upgrade (Mar 29 2026)**:
  - Multi-Tier Banking: Current Month + Reserve Bank (capped at 500 hrs)
  - Predictive Eligibility Alerts: Burn rate calc, months remaining, at-risk flags (<2x threshold)
  - Automated Bridge Payment Logic: Cash-to-hours conversion, instant member activation
  - Manual Hour Entry form (add/deduct hours with audit trail)
  - Claims Integration Gatekeeper: Hour bank check before adjudication; short-hour members routed to Examiner Queue with "Eligibility Hold"
  - Eligibility Source Tracking: Badges on claims (Standard Hours, Reserve Draw, Bridge Payment, Insufficient)
  - Bridge Payment Settings: Toggle + rate-per-hour config in Settings
  - Predictive Eligibility Dashboard: Summary cards + full member table in Reports
  - Enhanced Hour Bank Deficiency Report: Multi-tier columns, burn rate, months remaining, at-risk flags
  - All UI is 100% static with tabular-nums and fixed heights (zero layout jitter)

## Key Endpoints
- `POST /api/hour-bank/upload-work-report` — CSV ingestion
- `GET /api/hour-bank/{member_id}` — Multi-tier ledger
- `POST /api/hour-bank/{member_id}/manual-entry` — Manual hours
- `POST /api/hour-bank/{member_id}/bridge-payment` — Bridge payment
- `POST /api/hour-bank/run-monthly` — Monthly deduction cycle
- `GET /api/hour-bank/notifications/list` — Low-balance alerts
- `GET /api/settings/bridge-payment` — Bridge config
- `PUT /api/settings/bridge-payment` — Update bridge config
- `GET /api/reports/predictive-eligibility` — Predictive dashboard
- `GET /api/reports/hour-bank-deficiency` — Enhanced deficiency report

## Upcoming Tasks (Prioritized Backlog)
- **P1**: Carrier Bordereaux Reporting Module
- **P1**: Real X12 EDI parser (834/837/835)
- **P1**: Azure AD MSAL real credentials
- **P2**: Network repricing vs contracted rates
- **P2**: External billing system API integration
- **P3**: Member self-service portal

## Mocked/Stubbed
- Real X12 EDI parsing (mocked)
- MSAL Azure AD (JWT fallback)

## Test Reports
- Iterations 1-12: Core features, refactoring, sidebar, base hour bank (all passing)
- Iteration 13: Hour Bank Module Upgrade — 100% pass (11/11 backend, all frontend)
